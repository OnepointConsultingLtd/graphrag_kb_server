import re
from functools import partial
from typing import AsyncIterator, Callable, Awaitable, Union

import jiter
from together import AsyncTogether
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel

from lightrag.utils import TokenTracker

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.types import GPTKeywordExtractionFormat

from graphrag_kb_server.config import LightRAGModelType
from graphrag_kb_server.service.project_config_service import ProjectConfig
from graphrag_kb_server.model.chat_response import ResponseSchema
from graphrag_kb_server.logger import logger

from openrouter import OpenRouter
from openrouter.errors import OpenRouterError


def _gemini_contents(prompt, history_messages):
    contents = []
    for msg in history_messages or []:
        if "role" not in msg or "content" not in msg:
            continue
        role = "model" if msg["role"] in ("assistant", "model") else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    )
    return contents


async def gemini_model_func(
    prompt, system_prompt=None, history_messages=[], *, config: ProjectConfig, **kwargs
) -> str:
    # 1. Initialize the GenAI Client with the Gemini API Key of the project
    assert (
        config.gemini_api_key is not None
    ), "Please specify the GEMINI_API_KEY environment variable."
    client = genai.Client(api_key=config.gemini_api_key)

    if history_messages is None:
        history_messages = []

    # 2. Call the Gemini model with a separate system instruction so the
    # static prompt can be cached independently of the per-request user content.
    config_dict = {
        "max_output_tokens": 65000,
        "temperature": 0,
        "top_k": 8,
        # "thinking_config": types.ThinkingConfig(thinking_level="low")
    }
    if system_prompt:
        config_dict["system_instruction"] = system_prompt

    structured_output = "structured_output" in kwargs and kwargs["structured_output"]
    if structured_output:
        if (
            "structured_output_format" in kwargs
            and kwargs["structured_output_format"] is not None
        ):
            config_dict["response_schema"] = kwargs["structured_output_format"]
        elif structured_output is True:
            config_dict["response_schema"] = ResponseSchema
        config_dict["response_mime_type"] = "application/json"

    response = await client.aio.models.generate_content(
        model=config.lightrag_model,
        contents=_gemini_contents(prompt, history_messages),
        config=types.GenerateContentConfig(**config_dict),
    )

    # 3. Get token counts with null safety
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
    total_tokens = getattr(usage, "total_token_count", 0) or (
        prompt_tokens + completion_tokens
    )
    thinking_tokens = getattr(usage, "thoughts_token_count", 0) or 0
    cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0
    logger.info(
        f"[gemini] [{config.project_label}] {config.lightrag_model} tokens - input: {prompt_tokens:,} "
        f"(cached: {cached_tokens:,}), thinking: {thinking_tokens:,}, "
        f"output: {completion_tokens:,}, total: {total_tokens:,}"
    )

    token_counts = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }

    token_tracker = TokenTracker()

    token_tracker.add_usage(token_counts)

    if structured_output:
        # Simulate error temporarily
        return jiter.from_json(response.text.encode(encoding="utf-8"))
    # 5. Return the response text
    return response.text


def _is_anthropic_model(model_name: str) -> bool:
    """Anthropic models require explicit cache_control on OpenRouter.
    Other providers (Gemini, OpenAI, DeepSeek) use automatic caching."""
    name = model_name.lower()
    return name.startswith("anthropic/") or name.startswith("claude")


# Bare OpenAI model names: "gpt-..." or the reasoning series "o1", "o3-mini", "o4-mini", ...
_BARE_OPENAI_MODEL_PATTERN = re.compile(r"^(gpt|o\d)")


def _is_openai_model(model_name: str) -> bool:
    """OpenAI models enforce the strict JSON schema rules of structured outputs
    (``additionalProperties: false`` and every property required), unlike Gemini or Anthropic.
    Matches the OpenRouter ``openai/`` prefix or a bare OpenAI model name."""
    name = model_name.lower()
    return name.startswith("openai/") or bool(_BARE_OPENAI_MODEL_PATTERN.match(name))


def _build_reasoning_param(config: ProjectConfig) -> dict | None:
    """Return the OpenRouter ``reasoning`` parameter for the configured effort.

    Returns None when no effort is configured, so that the parameter is omitted and the
    model uses its own default. This matters because the accepted values differ per model
    (e.g. OpenAI GPT-5.1+ rejects "minimal").
    """
    reasoning_effort = (config.lightrag_reasoning_effort or "").strip()
    if not reasoning_effort:
        return None
    return {"effort": reasoning_effort}


def _build_json_schema_response_format(
    schema_model: type[BaseModel], strict: bool, openai_strict_schema: bool
) -> dict:
    """Build an OpenAI style ``response_format`` of type ``json_schema`` for a Pydantic model.

    ``strict`` sets the ``strict`` flag of the request. ``openai_strict_schema`` converts the
    schema with the OpenAI SDK's own converter, which adds ``additionalProperties: false`` to
    every object, makes every property required and removes defaults, as OpenAI's strict
    structured outputs require. Without it the plain Pydantic schema is sent (accepted by
    Gemini and Anthropic, also in strict mode).
    """
    schema_dict = (
        to_strict_json_schema(schema_model)
        if openai_strict_schema
        else schema_model.model_json_schema()
    )
    json_schema = {
        "name": schema_dict.get("title", schema_model.__name__),
        "schema": schema_dict,
    }
    if strict:
        json_schema["strict"] = True
    return {"type": "json_schema", "json_schema": json_schema}


def _log_openrouter_error(error: OpenRouterError, config: ProjectConfig) -> None:
    """Log the full OpenRouter error response.

    The SDK's error message is only the generic text (e.g. "Provider returned error"); the
    upstream provider's actual message is in the response body (``error.metadata.raw``).
    """
    logger.error(
        f"[{config.project_label}] OpenRouter call to {config.lightrag_model} failed with "
        f"status {error.status_code}: {error.message}. Response body: {error.body}"
    )


async def structured_completion(
    client: AsyncTogether | AsyncOpenAI | OpenRouter,
    prompt,
    system_prompt=None,
    history_messages=[],
    *,
    config: ProjectConfig,
    **kwargs,
) -> Union[str, dict, AsyncIterator[str]]:
    messages = []
    is_openai = isinstance(client, AsyncOpenAI)
    is_openrouter = isinstance(client, OpenRouter)
    model_name = config.lightrag_model
    needs_explicit_cache = is_openrouter and _is_anthropic_model(model_name)

    if system_prompt:
        if needs_explicit_cache:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
            )
        else:
            messages.append({"role": "system", "content": system_prompt})
    for msg in history_messages:
        if "role" in msg and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    structured_output = "structured_output" in kwargs and kwargs["structured_output"]
    stream = kwargs.get("stream", False)
    config_dict = {"model": model_name, "messages": messages}

    # Add provider parameter for OpenRouter if specified in config
    # OpenRouter expects provider as a dictionary matching ChatGenerationParamsProvider
    if is_openrouter and config.openrouter_provider:
        config_dict["provider"] = {"name": config.openrouter_provider}
    if is_openrouter:
        reasoning = _build_reasoning_param(config)
        if reasoning is not None:
            config_dict["reasoning"] = reasoning
    if structured_output:
        if is_openai or is_openrouter:
            # OpenAI requires nested json_schema structure with name
            schema_model = kwargs.get("structured_output_format") or ResponseSchema
            config_dict["response_format"] = _build_json_schema_response_format(
                schema_model,
                strict=is_openrouter,
                # OpenAI rejects a strict schema that does not follow its strict rules.
                openai_strict_schema=is_openrouter and _is_openai_model(model_name),
            )
        else:
            # Together AI uses simpler format
            config_dict["response_format"] = {"type": "json_schema"}
            if (
                "structured_output_format" in kwargs
                and kwargs["structured_output_format"] is not None
            ):
                config_dict["response_format"]["schema"] = kwargs[
                    "structured_output_format"
                ].model_json_schema()
            elif structured_output is True:
                config_dict["response_format"][
                    "schema"
                ] = ResponseSchema.model_json_schema()

    if stream:
        config_dict["stream"] = True

    logger.info(
        f"[{config.project_label}] Calling structured completion with config: {config_dict['model']}"
    )
    logger.debug(
        f"Calling structured completion with system prompt: {config_dict['messages'][0]['content']}"
    )
    if is_openrouter:
        try:
            response = await client.chat.send_async(**config_dict)
        except OpenRouterError as error:
            _log_openrouter_error(error, config)
            raise
    else:
        response = await client.chat.completions.create(**config_dict)

    if stream:
        return _stream_tokens(response, _client_ref=client)

    usage = getattr(response, "usage", None)
    prompt_details = getattr(usage, "prompt_tokens_details", None) or None
    completion_details = getattr(usage, "completion_tokens_details", None) or None
    logger.info(
        f"[structured_completion] [{config.project_label}] {model_name} tokens - "
        f"input: {int(getattr(usage, 'prompt_tokens', 0) or 0):,} "
        f"(cached: {int(getattr(prompt_details, 'cached_tokens', 0) or 0):,}), "
        f"thinking: {int(getattr(completion_details, 'reasoning_tokens', 0) or 0):,}, "
        f"output: {int(getattr(usage, 'completion_tokens', 0) or 0):,}, "
        f"total: {int(getattr(usage, 'total_tokens', 0) or 0):,}"
    )

    content = response.choices[0].message.content
    return (
        jiter.from_json(content.encode(encoding="utf-8"))
        if structured_output
        else content
    )


async def _stream_tokens(response_stream, _client_ref=None) -> AsyncIterator[str]:
    """Extract text content from streaming API response chunks.

    _client_ref prevents the API client from being garbage-collected
    while the async generator is alive (important for OpenRouter).
    """
    async for chunk in response_stream:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        if delta is None:
            continue
        content = getattr(delta, "content", None)
        if content:
            yield content


async def togetherai_model_func(
    prompt, system_prompt=None, history_messages=[], *, config: ProjectConfig, **kwargs
) -> Union[str, dict, AsyncIterator[str]]:
    client = AsyncTogether(api_key=config.togetherai_api_key)
    return await structured_completion(
        client, prompt, system_prompt, history_messages, config=config, **kwargs
    )


async def openai_model_func(
    prompt, system_prompt=None, history_messages=[], *, config: ProjectConfig, **kwargs
) -> Union[str, dict, AsyncIterator[str]]:
    # An empty key means "not configured": let the SDK fall back to its own lookup.
    client = AsyncOpenAI(api_key=config.openai_api_key or None)
    return await structured_completion(
        client, prompt, system_prompt, history_messages, config=config, **kwargs
    )


async def openrouter_model_func(
    prompt, system_prompt=None, history_messages=[], *, config: ProjectConfig, **kwargs
) -> Union[str, dict, AsyncIterator[str]]:
    if kwargs.get("stream", False):
        client = OpenRouter(api_key=config.openrouter_api_key)
        return await structured_completion(
            client, prompt, system_prompt, history_messages, config=config, **kwargs
        )
    with OpenRouter(api_key=config.openrouter_api_key) as client:
        return await structured_completion(
            client, prompt, system_prompt, history_messages, config=config, **kwargs
        )


def openai_model_func_factory(
    model: str, config: ProjectConfig
) -> Callable[..., Awaitable[str]]:
    async def openai_model_func(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        if history_messages is None:
            history_messages = []
        keyword_extraction = kwargs.pop("keyword_extraction", None)
        if keyword_extraction:
            kwargs["response_format"] = GPTKeywordExtractionFormat
        kwargs.setdefault("api_key", config.openai_api_key or None)
        return await openai_complete_if_cache(
            model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    return openai_model_func


def select_model_func(config: ProjectConfig) -> Callable[..., Awaitable[str]]:
    """Return the LLM function for the project, bound to the project's configuration.

    Raises ValueError for a model type / model combination which is not supported.
    """
    match config.lightrag_model_type:
        case LightRAGModelType.GOOGLE:
            return partial(gemini_model_func, config=config)
        case LightRAGModelType.OPENAI:
            if config.lightrag_model.startswith("gpt"):
                return partial(openai_model_func, config=config)
            raise ValueError(
                f"Unsupported OpenAI LightRAG model: {config.lightrag_model}"
            )
        case LightRAGModelType.TOGETHERAI:
            return partial(togetherai_model_func, config=config)
        case LightRAGModelType.OPENROUTER:
            return partial(openrouter_model_func, config=config)
        case _:
            raise ValueError(
                f"Invalid LightRAG model type: {config.lightrag_model_type}"
            )


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from graphrag_kb_server.model.search.search import SearchResults

    prompts_dir = Path(__file__).parent.parent.parent / "docs/prompts"

    async def main():
        prompts_file = prompts_dir / "prompts_20251029081051.json"
        with open(prompts_file, "r") as f:
            prompts = jiter.from_json(f.read().encode(encoding="utf-8"))
        print(prompts)
        response = await togetherai_model_func(
            prompts["prompt"],
            system_prompt=prompts["system_prompt"],
            history_messages=[],
            structured_output=True,
            structured_output_format=SearchResults,
            config=ProjectConfig.from_env(),
        )
        print(response)

    asyncio.run(main())

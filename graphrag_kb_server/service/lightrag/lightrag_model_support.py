import json
from typing import Callable, Awaitable

import jiter
from together import AsyncTogether
from google import genai
from google.genai import types
from openai import AsyncOpenAI

from lightrag.utils import TokenTracker

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.types import GPTKeywordExtractionFormat

from graphrag_kb_server.config import LightRAGModelType, cfg, lightrag_cfg
from graphrag_kb_server.model.chat_response import ResponseSchema
from graphrag_kb_server.logger import logger

from openrouter import OpenRouter


def _create_combined_prompt(system_prompt, history_messages, prompt):
    combined_prompt = ""
    if system_prompt:
        combined_prompt += f"{system_prompt}\n"

    for msg in history_messages:
        # Each msg is expected to be a dict: {"role": "...", "content": "..."}
        combined_prompt += f"{msg['role']}: {msg['content']}\n"

    # Finally, add the new user prompt
    combined_prompt += f"user: {prompt}"
    return combined_prompt


async def gemini_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    # 1. Initialize the GenAI Client with your Gemini API Key
    assert (
        cfg.gemini_api_key is not None
    ), "Please specify the GEMINI_API_KEY environment variable."
    client = genai.Client(api_key=cfg.gemini_api_key)

    # 2. Combine prompts: system prompt, history, and user prompt
    if history_messages is None:
        history_messages = []

    combined_prompt = _create_combined_prompt(system_prompt, history_messages, prompt)
    # _store_prompts(system_prompt, history_messages, prompt)

    # 3. Call the Gemini model
    config_dict = {"max_output_tokens": 65000, "temperature": 0, "top_k": 8}

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
        model=lightrag_cfg.lightrag_model,
        contents=[combined_prompt],
        config=types.GenerateContentConfig(**config_dict),
    )

    # 4. Get token counts with null safety
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
    total_tokens = getattr(usage, "total_token_count", 0) or (
        prompt_tokens + completion_tokens
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


async def structured_completion(
    client: AsyncTogether | AsyncOpenAI | OpenRouter,
    prompt,
    system_prompt=None,
    history_messages=[],
    **kwargs,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for msg in history_messages:
        if "role" in msg and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    structured_output = "structured_output" in kwargs and kwargs["structured_output"]
    config_dict = {
        "model": lightrag_cfg.lightrag_model,
        "messages": messages
    }
    # Detect client type to use appropriate format
    is_openai = isinstance(client, AsyncOpenAI)
    is_openrouter = isinstance(client, OpenRouter)
    
    # Add provider parameter for OpenRouter if specified in config
    # OpenRouter expects provider as a dictionary matching ChatGenerationParamsProvider
    if is_openrouter and cfg.openrouter_provider:
        config_dict["provider"] = {"name": cfg.openrouter_provider}
    if structured_output:
        if is_openai or is_openrouter:
            # OpenAI requires nested json_schema structure with name
            if (
                "structured_output_format" in kwargs
                and kwargs["structured_output_format"] is not None
            ):
                schema_model = kwargs["structured_output_format"]
                schema_dict = schema_model.model_json_schema()
                # Extract name from schema title or use class name
                schema_name = schema_dict.get("title", schema_model.__name__)
            else:
                # Default to ResponseSchema if no format specified
                schema_dict = ResponseSchema.model_json_schema()
                schema_name = schema_dict.get("title", ResponseSchema.__name__)

            config_dict["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": schema_dict},
            }
            if is_openrouter:
                config_dict["response_format"]["json_schema"]["strict"] = True
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
    logger.info(f"Calling structured completion with config: {config_dict['model']}")
    logger.debug(f"Calling structured completion with system prompt: {config_dict['messages'][0]['content']}")
    if is_openrouter:
        response = await client.chat.send_async(**config_dict)
    else:
        response = await client.chat.completions.create(**config_dict)
    content = response.choices[0].message.content
    return jiter.from_json(content.encode(encoding="utf-8")) if structured_output else content


async def togetherai_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    client = AsyncTogether(api_key=cfg.togetherai_api_key)
    return await structured_completion(
        client, prompt, system_prompt, history_messages, **kwargs
    )


async def openai_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    client = AsyncOpenAI()
    return await structured_completion(
        client, prompt, system_prompt, history_messages, **kwargs
    )


async def openrouter_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    with OpenRouter(
        api_key=cfg.openrouter_api_key
    ) as client:
        return await structured_completion(
            client, prompt, system_prompt, history_messages, **kwargs
        )

def openai_model_func_factory(model: str) -> Callable[..., Awaitable[str]]:
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
        return await openai_complete_if_cache(
            model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    return openai_model_func


def select_model_func() -> Callable[..., Awaitable[str]]:
    match lightrag_cfg.lightrag_model_type:
        case LightRAGModelType.GOOGLE:
            return gemini_model_func
        case LightRAGModelType.OPENAI:
            match lightrag_cfg.lightrag_model:
                case "gpt-4o-mini":
                    return openai_model_func
                case "gpt-4o":
                    return openai_model_func
                case model if model.startswith("gpt"):
                    return openai_model_func
        case LightRAGModelType.TOGETHERAI:
            return togetherai_model_func
        case LightRAGModelType.OPENROUTER:
            return openrouter_model_func
        case _:
            raise ValueError(
                f"Invalid LightRAG model type: {lightrag_cfg.lightrag_model_type}"
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
        )
        print(response)

    asyncio.run(main())

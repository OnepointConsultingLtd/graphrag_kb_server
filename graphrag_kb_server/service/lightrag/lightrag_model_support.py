import json
from typing import Callable, Awaitable

from google import genai
from google.genai import types

from lightrag.utils import TokenTracker
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.types import GPTKeywordExtractionFormat
from pydantic import BaseModel, Field

from graphrag_kb_server.config import cfg, lightrag_cfg


class Reference(BaseModel):
    type: str = Field(description="The type of the reference")
    main_keyword: str = Field(description="The main keyword or topic of the reference")
    file: str = Field(description="The file of the reference")


class ResponseSchema(BaseModel):
    response: str = Field(description="The response to the user's question")
    references: list[Reference] = Field(
        description="The references to the user's question"
    )


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

    combined_prompt = ""
    if system_prompt:
        combined_prompt += f"{system_prompt}\n"

    for msg in history_messages:
        # Each msg is expected to be a dict: {"role": "...", "content": "..."}
        combined_prompt += f"{msg['role']}: {msg['content']}\n"

    # Finally, add the new user prompt
    combined_prompt += f"user: {prompt}"

    # 3. Call the Gemini model
    config_dict = {"max_output_tokens": 65000, "temperature": 0, "top_k": 8}

    structured_output = "structured_output" in kwargs and kwargs["structured_output"]
    if structured_output:
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
        return json.loads(response.text)
    # 5. Return the response text
    return response.text


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
    match lightrag_cfg.lightrag_model:
        case "gpt-4o-mini":
            return gpt_4o_mini_complete
        case "gpt-4o":
            return gpt_4o_complete
        case model if model.startswith("gemini"):
            return gemini_model_func
        case model if model.startswith("gpt"):
            return openai_model_func_factory(model)
        case _:
            raise ValueError(f"Invalid LightRAG model: {lightrag_cfg.lightrag_model}")

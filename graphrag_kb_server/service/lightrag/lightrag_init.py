from pathlib import Path
import json

from pydantic import BaseModel, Field
from lightrag import LightRAG
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import TokenTracker

from google import genai
from google.genai import types

from graphrag_kb_server.config import cfg, lightrag_cfg
from graphrag_kb_server.utils.cache import GenericSimpleCache


lightrag_cache = GenericSimpleCache[LightRAG]()


class Reference(BaseModel):
    type: str = Field(description="The type of the reference")
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
    config_dict = {"max_output_tokens": 5000, "temperature": 0, "top_k": 10}
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
        return json.loads(response.text)
    # 5. Return the response text
    return response.text


async def initialize_rag(project_folder: Path) -> LightRAG:
    lightrag = lightrag_cache.get(project_folder)
    if lightrag:
        return lightrag
    working_dir = project_folder / LIGHTRAG_FOLDER
    if not working_dir.exists():
        working_dir.mkdir(parents=True, exist_ok=True)
    llm_model_func = gpt_4o_mini_complete
    match lightrag_cfg.lightrag_model:
        case "gpt-4o-mini":
            llm_model_func = gpt_4o_mini_complete
        case "gpt-4o":
            llm_model_func = gpt_4o_complete
        case model if model.startswith("gemini"):
            llm_model_func = gemini_model_func
        case _:
            raise ValueError(f"Invalid LightRAG model: {lightrag_cfg.lightrag_model}")
    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=openai_embed,
        llm_model_func=llm_model_func,
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()
    lightrag_cache.set(project_folder, rag)
    # Disable LLM cache for now
    rag.llm_response_cache.global_config["enable_llm_cache"] = False
    return rag

import uuid
from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, Field

from graphrag_kb_server.callbacks.callback_support import BaseCallback
from lightrag import QueryParam

from graphrag_kb_server.model.engines import Engine


class MessageType(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ContextFormat(StrEnum):
    JSON_STRING = "json_string"
    JSON = "json"


class ContextParameters(BaseModel):
    query: str = Field(description="The query fpr which the context is retrieved.")
    project_dir: Path = Field(description="The path of the project.")
    context_size: int = Field(default=5000, description="The context size in tokens.")
    model_config = {"frozen": True}  # Pydantic v2 config syntax
    context_format: ContextFormat = Field(default=ContextFormat.JSON_STRING, description="The format of the response.")


class QueryParameters(BaseModel):
    format: str = Field(description="The format of the response.")
    search: str = Field(description="The search type.")
    engine: Engine = Field(description="The engine to use.")
    context_params: ContextParameters = Field(description="The context parameters.")
    system_prompt: str | None = Field(
        default=None,
        description="The system prompt to use.",
    )
    system_prompt_additional: str | None = Field(
        default="",
        description="Additional instructions to the LLM. This will not override the original system prompt.",
    )
    hl_keywords: list[str] = Field(
        default=[],
        description="High-level keywords to add to the query.",
    )
    ll_keywords: list[str] = Field(
        default=[],
        description="Low-level keywords to add to the query.",
    )
    include_context: bool = Field(
        default=False, description="Whether to include the context in the response."
    )
    include_context_as_text: bool = Field(
        default=False,
        description="Whether to include the context as text in the response.",
    )
    structured_output: bool = Field(
        default=False,
        description="Whether to use structured output.",
    )
    chat_history: list[dict[str, str]] = Field(
        default=[],
        description="The chat history.",
    )
    conversation_id: str = Field(
        default=str(uuid.uuid4()),
        description="The conversation id.",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response.",
    )
    model_config = {"frozen": True}  # Pydantic v2 config syntax
    keywords: bool = Field(
        default=False,
        description="Whether to append the keywords to the context.",
    )
    max_filepath_depth: int = Field(
        default=50,
        description="The maximum length of the file path to include in the context.",
    )
    is_search_query: bool = Field(
        default=False,
        description="Whether the query is a search query.",
    )
    callback: BaseCallback | None = Field(
        default=None,
        description="The callback to use in the context of websockets",
    )
    max_entity_size: int = Field(
        default=1000,
        description="The maximum number of entities to include in the context.",
    )
    max_relation_size: int = Field(
        default=1000,
        description="The maximum number of relations to include in the context.",
    )
    context_format: ContextFormat = Field(default=ContextFormat.JSON_STRING, description="The format of the response.")


def convert_to_lightrag_query_params(
    query_params: QueryParameters, only_need_context: bool = False
) -> QueryParam:
    param = QueryParam(
        mode=query_params.search,
        only_need_context=only_need_context,
        hl_keywords=query_params.hl_keywords,
        ll_keywords=query_params.ll_keywords,
        conversation_history=query_params.chat_history,
    )
    return param

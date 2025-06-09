from pathlib import Path
from pydantic import BaseModel, Field
from graphrag_kb_server.model.engines import Engine


class ContextParameters(BaseModel):
    query: str = Field(description="The query fpr which the context is retrieved.")
    project_dir: Path = Field(description="The path of the project.")
    context_size: int = Field(description="The context size in tokens.")


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

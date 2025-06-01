from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from graphrag_kb_server.model.engines import Engine
from lightrag.operate import PROMPTS


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
        default=PROMPTS["rag_response"],
        description="The system prompt to use for the chat.",
    )

    @field_validator("system_prompt")
    def validate_system_prompt(cls, v: str | None) -> str:
        if not v or v.strip() == "":
            return PROMPTS["rag_response"]
        return v

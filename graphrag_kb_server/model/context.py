from typing import Optional
from enum import StrEnum
from pydantic import BaseModel, Field
from graphrag.query.context_builder.builders import ContextBuilderResult


class ContextResult(BaseModel):
    context_text: str = Field(description="The context as a string")
    local_context_records: Optional[dict] = Field(
        description="The optional local context records"
    )
    global_context_records: Optional[dict] = Field(
        description="The optional global context records"
    )


class Search(StrEnum):
    LOCAL = "local"
    GLOBAL = "global"
    DRIFT = "drift"
    ALL = "all"
    NAIVE = "naive"


def convert_to_str(context_chunks: str | list[str]) -> str:
    if isinstance(context_chunks, list):
        return "\n".join(context_chunks)
    return context_chunks


def create_context_result(
    context_builder_result: ContextBuilderResult, search: Search
) -> ContextResult:
    params = {"context_text": convert_to_str(context_builder_result.context_chunks)}
    match search:
        case Search.LOCAL:
            params["local_context_records"] = context_builder_result.context_records
            params["global_context_records"] = None
        case Search.GLOBAL:
            params["global_context_records"] = context_builder_result.context_records
            params["local_context_records"] = None
    return ContextResult(**params)


def create_global_context_result(
    local_builder_result: ContextResult,
    global_builder_result: ContextResult,
) -> ContextResult:
    template = """
# LOCAL CONTEXT

{local_context_text}

# GLOBAL CONTEXT

{global_context_text}
"""
    context_text = template.format(
        local_context_text=convert_to_str(local_builder_result.context_text),
        global_context_text=convert_to_str(global_builder_result.context_text),
    )
    return ContextResult(
        context_text=context_text,
        local_context_records=local_builder_result.local_context_records,
        global_context_records=global_builder_result.global_context_records,
    )

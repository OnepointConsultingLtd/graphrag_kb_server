from graphrag.query.context_builder.builders import ContextBuilderResult
from graphrag_kb_server.model.context import (
    create_context_result,
    create_global_context_result,
    Search,
    ContextResult,
)


def test_create_context_result():
    builder_result = ContextBuilderResult(
        context_chunks="test", context_records={"test": "test"}
    )
    context_result = create_context_result(builder_result, Search.LOCAL)
    assert context_result.context_text is not None, "Context text should exist"
    assert (
        context_result.context_text == builder_result.context_chunks
    ), "Context text does not match context chunks"
    assert (
        context_result.local_context_records == builder_result.context_records
    ), "Local context records should exist."
    assert (
        context_result.global_context_records is None
    ), "The global context records should not exist."


def test_create_global_context_result():
    local_result = ContextResult(
        context_text="Some local context",
        local_context_records={"test": "local"},
        global_context_records={},
    )
    global_result = ContextResult(
        context_text="Some global context",
        local_context_records={},
        global_context_records={"test": "global"},
    )
    context_result = create_global_context_result(local_result, global_result)
    assert context_result is not None, "There is not context result"
    assert context_result.context_text is not None, "There is no context text."
    assert "local" in context_result.context_text, "Cannot find local in context text."
    assert (
        "global" in context_result.context_text
    ), "Cannot find global in context text."
    assert (
        context_result.global_context_records is not None
    ), "There are no global context records."
    assert (
        context_result.local_context_records is not None
    ), "There are no local context records."
    assert "local" in context_result.local_context_records.values()
    assert "global" in context_result.global_context_records.values()

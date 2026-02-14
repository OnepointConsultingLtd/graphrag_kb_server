from graphrag_kb_server.model.context import (
    create_global_context_result,
    ContextResult,
)


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

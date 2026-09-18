from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.lightrag.lightrag_search import (
    PROMPTS,
    build_dynamic_user_prompt,
    build_static_system_prompt,
)


def test_static_system_prompt_puts_role_first():
    additional = "Always use British English."
    result = build_static_system_prompt(PROMPTS["document-retrieval"], additional)

    additional_idx = result.index("Always use British English.")
    role_idx = result.index("---Role---")
    assert result.startswith("---Role---")
    assert role_idx < additional_idx
    assert result.index("Additional Instructions:") > role_idx
    assert "{context_data}" not in result
    assert "{response_type}" not in result
    assert "{user_prompt}" not in result


def test_static_system_prompt_has_no_context_placeholder():
    result = build_static_system_prompt(PROMPTS["rag_response"], "")
    assert "{context_data}" not in result
    assert "---Knowledge Graph and Document Chunks---" not in result


def test_static_system_prompt_is_cache_stable_across_queries():
    additional = prompts["document-retrieval"]["system_prompt_additional"]
    first = build_static_system_prompt(PROMPTS["document-retrieval"], additional)
    second = build_static_system_prompt(PROMPTS["document-retrieval"], additional)
    assert first == second


def test_dynamic_user_prompt_contains_date_context_and_query_in_order():
    result = build_dynamic_user_prompt(
        context='{"entity": "SAP"}',
        query="How can I use AI?",
        response_type="Multiple Paragraphs",
        user_prompt="n/a",
        date="2026-09-18",
    )

    date_idx = result.index("The current date is 2026-09-18")
    context_idx = result.index("---Knowledge Graph and Document Chunks---")
    query_idx = result.index("---User Query---")
    assert date_idx < context_idx < query_idx
    assert '{"entity": "SAP"}' in result
    assert "How can I use AI?" in result
    assert "Target format: Multiple Paragraphs" in result


def test_document_retrieval_assembly_keeps_toml_instructions_in_system():
    additional = prompts["document-retrieval"]["system_prompt_additional"]
    system = build_static_system_prompt(PROMPTS["document-retrieval"], additional)
    user = build_dynamic_user_prompt(
        context="chunk-json",
        query="find relevant documents",
        response_type="Multiple Paragraphs",
        user_prompt="n/a",
        date="2026-09-18",
    )

    assert "When retrieving documents in response to the user's question" in system
    assert system.index("---Role---") < system.index("Additional Instructions:")
    assert "{context_data}" not in system
    assert "chunk-json" not in system
    assert "chunk-json" in user
    assert "find relevant documents" in user
    assert "The current date is 2026-09-18" in user
    assert "The current date is 2026-09-18" not in system

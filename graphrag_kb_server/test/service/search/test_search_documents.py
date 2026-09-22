from graphrag_kb_server.service.search.search_documents import (
    generate_question,
    _as_document_search_response,
)
from graphrag_kb_server.test.provider.search_provider import (
    create_document_search_query,
)


def test_generate_question():
    query = create_document_search_query()
    generated_question = generate_question(query)
    assert generated_question is not None, "No query returned"
    assert isinstance(generated_question, str), "Query is not a string"
    print(generated_question)


def test_as_document_search_response_from_string():
    payload = _as_document_search_response("Sorry, I don't know.")
    assert payload["documents"] == []
    assert payload["response"] == "Sorry, I don't know."


def test_as_document_search_response_from_empty():
    payload = _as_document_search_response(None)
    assert payload["documents"] == []
    assert payload["response"] == "No relevant documents were found."


def test_as_document_search_response_from_dict():
    original = {
        "documents": [{"relevancy_score": "high", "summary": "x"}],
        "response": "Here are the results.",
    }
    payload = _as_document_search_response(original)
    assert payload["documents"] == original["documents"]
    assert payload["response"] == "Here are the results."

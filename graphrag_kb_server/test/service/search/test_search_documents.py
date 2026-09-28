from graphrag_kb_server.service.search.search_documents import (
    generate_question,
    _as_document_search_response,
    _map_reference_ids,
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


def test_map_reference_ids_known_and_unknown():
    documents = [
        {"reference_id": "1", "summary": "a", "relevancy_score": "high"},
        {"reference_id": "9", "summary": "b", "relevancy_score": "low"},
    ]
    references = [
        {"reference_id": "1", "file_path": "/var/docs/a.txt"},
        {"reference_id": "2", "file_path": "/var/docs/b.txt"},
    ]
    mapped = _map_reference_ids(documents, references)
    assert mapped == [
        {
            "summary": "a",
            "relevancy_score": "high",
            "document_path": "/var/docs/a.txt",
            "links": [],
        }
    ]


def test_map_reference_ids_without_references():
    documents = [{"reference_id": "1", "summary": "a"}]
    assert _map_reference_ids(documents, None) == []

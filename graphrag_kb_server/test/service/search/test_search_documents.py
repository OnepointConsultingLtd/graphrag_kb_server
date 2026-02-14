from graphrag_kb_server.test.provider.search_provider import (
    create_document_search_query,
)


def test_generate_question():
    from graphrag_kb_server.service.search.search_documents import generate_question

    query = create_document_search_query()
    generated_question = generate_question(query)
    assert generated_question is not None, "No query returned"
    assert isinstance(generated_question, str), "Query is not a string"
    print(generated_question)

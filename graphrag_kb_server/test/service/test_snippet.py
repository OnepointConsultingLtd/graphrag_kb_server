from graphrag_kb_server.service.snippet_generation_service import generate_snippet
from graphrag_kb_server.test.provider.snippet_provider import create_snippet


def test_snippet_generation():
    root_element_id, jwt_token, snippet = create_snippet()
    generated = generate_snippet(snippet)
    assert generated is not None
    assert isinstance(generated, str)
    assert root_element_id in generated
    assert jwt_token in generated

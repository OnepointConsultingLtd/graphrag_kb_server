from graphrag_kb_server.test.model.match_query_provider import create_match_query
from graphrag_kb_server.model.digest_functions import content_sha256


def test_content_sha256():
    match_query = create_match_query()
    digest = content_sha256(match_query)
    assert digest is not None, "No digest returned"
    assert isinstance(digest, str), "Digest is not a string"
    print(digest)
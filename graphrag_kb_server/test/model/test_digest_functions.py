from graphrag_kb_server.model.digest_functions import content_sha256


def test_content_sha256():
    digest = content_sha256("Test")
    assert digest is not None, "No digest returned"
    assert isinstance(digest[0], str), "Digest is not a string"

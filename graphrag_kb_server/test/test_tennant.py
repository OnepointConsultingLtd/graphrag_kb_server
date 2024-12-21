import asyncio

from graphrag_kb_server.test.provider.tennant_provider import regenerate_test_tennant
from graphrag_kb_server.service.jwt_service import generate_token
from graphrag_kb_server.service.tennant import list_tennants


def test_tennant_create():
    _, token_data = regenerate_test_tennant()
    asyncio.run(generate_token(token_data))
    tennants = list_tennants()
    assert tennants is not None, "Tennants should not be none"
    assert len(tennants) > 0

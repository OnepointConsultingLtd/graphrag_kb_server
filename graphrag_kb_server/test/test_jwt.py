import asyncio

from graphrag_kb_server.model.jwt_token import JWTToken
from graphrag_kb_server.model.error import Error

from graphrag_kb_server.test.provider.tennant_provider import regenerate_test_tennant


def test_rename_to_folder():
    from graphrag_kb_server.service.jwt_service import rename_to_folder
    assert rename_to_folder("this is a long name. ") == "this_is_a_long_name_"
    assert rename_to_folder(" 123%$") == "123__"


def test_generate_token():
    from graphrag_kb_server.service.jwt_service import generate_token, decode_token
    folder_name, token_data = regenerate_test_tennant()
    token = asyncio.run(generate_token(token_data))
    assert token is not None
    decoded = asyncio.run(decode_token(token.token))
    assert "sub" in decoded, "Cannot find folder name in decoded token"
    assert decoded["sub"] == folder_name


def test_generate_token_twice():
    from graphrag_kb_server.service.jwt_service import generate_token, decode_token
    _, token_data = regenerate_test_tennant()
    token = asyncio.run(generate_token(token_data))
    assert token is not None
    assert isinstance(token, JWTToken)
    decoded = asyncio.run(decode_token(token.token))
    assert "permissions" in decoded, "Cannot find permissions in decoded token"
    assert decoded["permissions"] == [
        "read",
        "write",
    ], "The token should have read and write permissions"
    error = asyncio.run(generate_token(token_data))
    assert error is not None
    assert isinstance(error, Error), "The result of the operation should be an error"


def test_generate_read_only_token():
    from graphrag_kb_server.service.jwt_service import generate_token, decode_token
    _, token_data = regenerate_test_tennant()
    token = asyncio.run(
        generate_token(token_data, generate_folder=False, read_only=True)
    )
    assert token is not None
    assert isinstance(token, JWTToken)
    decoded = asyncio.run(decode_token(token.token))
    assert decoded["permissions"] == [
        "read"
    ], "The token should have read and write permissions"

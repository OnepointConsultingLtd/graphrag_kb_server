import asyncio
import shutil

from graphrag_kb_server.model.jwt_token import JWTTokenData
from graphrag_kb_server.service.jwt import (
    rename_to_folder,
    generate_token,
    decode_token,
)
from graphrag_kb_server.config import cfg


def test_rename_to_folder():
    assert rename_to_folder("this is a long name. ") == "this_is_a_long_name_"
    assert rename_to_folder(" 123%$") == "123__"


def test_generate_token():
    folder_name = "test"
    folder_path = cfg.graphrag_root_dir_path / folder_name
    shutil.rmtree(folder_path)
    token_data = JWTTokenData(
        name=folder_name, email="test@test.com", time_delta_minutes=None
    )
    token = asyncio.run(generate_token(token_data))
    assert token is not None
    decoded = asyncio.run(decode_token(token.token))
    assert "sub" in decoded, "Cannot find folder name in decoded token"
    assert decoded["sub"] == folder_name

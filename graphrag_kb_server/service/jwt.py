import time
import re
from datetime import datetime, timedelta, timezone

import jwt
from graphrag_kb_server.config import cfg, jwt_cfg
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error, ErrorCode


TENNANT_JSON = "tennant.json"


def rename_to_folder(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.strip())


async def generate_token(token_data: JWTTokenData) -> JWTToken | Error:
    name, email, time_delta_minutes = (
        token_data.name,
        token_data.email,
        token_data.time_delta_minutes,
    )
    folder_name = rename_to_folder(name)
    payload = {"sub": str(folder_name), "name": name, "iat": int(time.time())}
    if time_delta_minutes is not None:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            seconds=time_delta_minutes
        )
    token = jwt.encode(payload, jwt_cfg.secret, jwt_cfg.algorithm)
    jwt_token = JWTToken(folder_name=folder_name, email=email, token=token)
    result = insert_jwt_token(jwt_token)
    if isinstance(result, Error):
        return result
    return jwt_token


def insert_jwt_token(jwt_token: JWTToken) -> str | Error:
    folder_name = jwt_token.folder_name
    folder_path = cfg.graphrag_root_dir_path / folder_name
    if not folder_path.exists():
        folder_path.mkdir()
        descriptor = folder_path / TENNANT_JSON
        descriptor.write_text(jwt_token.json(), encoding="utf-8")
    else:
        return Error(
            error_code=ErrorCode.PROJECT_EXISTS,
            error="Folder exists",
            description=f"Folder {folder_name} already exists. Choose another one.",
        )
    return folder_name


async def decode_token(token: str) -> dict:
    return jwt.decode(token, jwt_cfg.secret, jwt_cfg.algorithm)

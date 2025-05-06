import time
import re
from datetime import datetime, timedelta, timezone

import jwt
from graphrag_kb_server.config import jwt_cfg
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error
from graphrag_kb_server.service.tennant import create_tennant_folder


def rename_to_folder(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


async def generate_token(
    token_data: JWTTokenData, generate_folder: bool = True
) -> JWTToken | Error:
    name, email, time_delta_minutes = (
        token_data.name,
        token_data.email,
        token_data.time_delta_minutes,
    )
    folder_name = rename_to_folder(name)
    payload = {
        "sub": str(folder_name),
        "name": name,
        "iat": int(time.time()),
        "email": email,
    }
    if time_delta_minutes is not None:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            seconds=time_delta_minutes
        )
    token = jwt.encode(payload, jwt_cfg.secret, jwt_cfg.algorithm)
    jwt_token = JWTToken(folder_name=folder_name, email=email, token=token)
    if generate_folder:
        result = create_tennant_folder(jwt_token)
        if isinstance(result, Error):
            return result
    return jwt_token


async def decode_token(token: str) -> dict:
    return jwt.decode(token, jwt_cfg.secret, jwt_cfg.algorithm)

import time
import re
import os
import asyncio
from datetime import datetime, timedelta, timezone

import jwt
from graphrag_kb_server.config import jwt_cfg, cfg
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error
from graphrag_kb_server.service.tennant import create_tennant_folder
from graphrag_kb_server.logger import logger


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


def generate_admin_token():
    jwt_cfg.admin_jwt = os.getenv("ADMIN_JWT")
    if jwt_cfg.admin_jwt is None or jwt_cfg.admin_jwt.strip() == "":
        logger.warning("ADMIN_JWT is not set, generating")
        jwt_cfg.admin_token_name = os.getenv("ADMIN_TOKEN_NAME")
        jwt_cfg.admin_token_email = os.getenv("ADMIN_TOKEN_EMAIL")
        if jwt_cfg.admin_token_name is None or jwt_cfg.admin_token_email is None:
            raise ValueError(
                "ADMIN_TOKEN_NAME and ADMIN_TOKEN_EMAIL must be set if ADMIN_JWT is not set."
            )
        jwt_cfg.admin_jwt = asyncio.run(
            generate_token(
                JWTTokenData(
                    name=jwt_cfg.admin_token_name, email=jwt_cfg.admin_token_email
                ),
                False,
            )
        )
        administration_yaml = cfg.config_dir / "administration.yaml"
        with open(administration_yaml, "w") as f:
            f.write(f"administrators:\n  - {jwt_cfg.admin_token_email}\n")
        logger.warning(f"ADMIN_JWT is now set to {jwt_cfg.admin_jwt}")

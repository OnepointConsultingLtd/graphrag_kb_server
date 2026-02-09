import time
import re
import os
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from graphrag_kb_server.config import jwt_cfg, cfg, admin_cfg
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.tennant import Tennant


def rename_to_folder(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


async def generate_token(
    token_data: JWTTokenData, generate_folder: bool = True, read_only: bool = False
) -> JWTToken | Error:
    from graphrag_kb_server.service.tennant import create_tennant_folder
    from graphrag_kb_server.main.bootstrap import create_tennant_tables

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
    if read_only:
        payload["permissions"] = ["read"]
    else:
        payload["permissions"] = ["read", "write"]
    if time_delta_minutes is not None:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            seconds=time_delta_minutes
        )
    token = jwt.encode(payload, jwt_cfg.secret, jwt_cfg.algorithm)
    jwt_token = JWTToken(folder_name=folder_name, email=email, token=token)
    if generate_folder:
        result = create_tennant_folder(jwt_token)
        tennant = Tennant(
            folder_name=folder_name,
            creation_timestamp=datetime.now(timezone.utc),
            token=token,
        )
        await create_tennant_tables(tennant)
        if isinstance(result, Error):
            return result
    return jwt_token


async def decode_token(token: str) -> dict:
    return jwt.decode(token, jwt_cfg.secret, jwt_cfg.algorithm)


def save_token_file(token: JWTToken, token_file: str, name: str, email: str):
    print("Token:")
    print(token.token)
    with open(cfg.config_dir / token_file, "wt", encoding="utf-8") as f:
        f.write("# Administration Token\n\n")
        f.write("- Token: ")
        f.write(token.token)
        f.write("\n- Name: ")
        f.write(name)
        f.write("\n- Email: ")
        f.write(email)


TOKEN_FILE = "administration_token.txt"


def save_security_yaml():
    security_yaml = cfg.config_dir / "security.yaml"
    if not security_yaml.exists():
        original_security_yaml = (
            Path(__file__).parent.parent.parent / "config" / "security.yaml"
        )
        if not original_security_yaml.exists():
            raise FileNotFoundError(
                f"Security file {original_security_yaml.as_posix()} not found"
            )
        shutil.copyfile(original_security_yaml, security_yaml)

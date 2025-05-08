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


def generate_admin_token():
    jwt_cfg.admin_jwt = os.getenv("ADMIN_JWT")
    administration_token_file = cfg.config_dir / TOKEN_FILE
    # Read the already saved token
    if administration_token_file.exists():
        with open(administration_token_file, "r", encoding="utf-8") as f:
            for line in f:
                if "Token:" in line:
                    jwt_cfg.admin_jwt = line.split(":")[1].strip()
                    break
        return  #
    logger.warning(
        f"{administration_token_file.as_posix()} does not exist, generating new token"
    )
    # Generate the token from the environment variables
    if jwt_cfg.admin_jwt is None or jwt_cfg.admin_jwt.strip() == "":
        logger.warning("ADMIN_JWT is not set, generating")
        if jwt_cfg.admin_token_name is None or jwt_cfg.admin_token_email is None:
            raise ValueError(
                "ADMIN_TOKEN_NAME and ADMIN_TOKEN_EMAIL must be set if ADMIN_JWT is not set."
            )
        jwt_token = asyncio.run(
            generate_token(
                JWTTokenData(
                    name=jwt_cfg.admin_token_name, email=jwt_cfg.admin_token_email
                ),
                False,
            )
        )
        jwt_cfg.admin_jwt = jwt_token.token
        administration_yaml = cfg.config_dir / "administration.yaml"
        with open(administration_yaml, "w") as f:
            admin = jwt_cfg.admin_token_email
            f.write(f"administrators:\n  - {admin}\n")
            admin_cfg.administrators.append(admin)
        logger.warning(f"ADMIN_JWT is now set to {jwt_cfg.admin_jwt}")
        save_token_file(
            jwt_token, TOKEN_FILE, jwt_cfg.admin_token_name, jwt_cfg.admin_token_email
        )
    else:
        logger.warning(f"ADMIN_JWT is already set to {jwt_cfg.admin_jwt}")


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

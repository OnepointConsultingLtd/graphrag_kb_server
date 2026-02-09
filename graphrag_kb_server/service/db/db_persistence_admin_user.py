from graphrag_kb_server.config import jwt_cfg
from graphrag_kb_server.model.admin import AdminUser
from graphrag_kb_server.model.jwt_token import JWTTokenData
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    fetch_all,
    fetch_one,
)
from graphrag_kb_server.service.jwt_service import generate_token
from graphrag_kb_server.service.validations import generate_hash

TB_ADMIN_USERS = "TB_ADMIN_USERS"


async def create_admin_user_table():
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS public.{TB_ADMIN_USERS} (
	ID SERIAL NOT NULL,
	NAME CHARACTER VARYING(100) NOT NULL,
	EMAIL CHARACTER VARYING(100) NOT NULL UNIQUE,
    PASSWORD_HASH TEXT NOT NULL,
    JWT_TOKEN TEXT NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (EMAIL)
);
"""
    )


async def drop_admin_user_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_ADMIN_USERS};
"""
    )


async def insert_admin_user(admin_user: AdminUser):
    password_hash = generate_hash(admin_user.password_plain)
    admin_user.password_hash = password_hash
    jwt_token = await generate_token(
        JWTTokenData(name=admin_user.name, email=admin_user.email), False
    )
    await execute_query(
        f"""
INSERT INTO public.{TB_ADMIN_USERS} (NAME, EMAIL, PASSWORD_HASH, JWT_TOKEN) VALUES ($1, $2, $3, $4);
""",
        admin_user.name,
        admin_user.email,
        admin_user.password_hash,
        jwt_token.token,
    )


async def delete_admin_user(email: str) -> bool:
    if email == jwt_cfg.admin_token_email:
        raise ValueError("Cannot delete the initial admin user")
    result = await execute_query(
        f"""
DELETE FROM public.{TB_ADMIN_USERS} WHERE EMAIL = $1;
""",
        email,
    )
    return result.split()[1] == "1"


async def select_admin_user(email: str) -> AdminUser | None:
    result = await fetch_one(
        f"""
SELECT * FROM public.{TB_ADMIN_USERS} WHERE EMAIL = $1;
""",
        email,
    )
    return (
        AdminUser(
            name=result.get("name"),
            email=result.get("email"),
            password_plain="",  # We don't need to return the password plain text
            password_hash=result.get("password_hash"),
            jwt_token=result.get("jwt_token"),
        )
        if result
        else None
    )


async def select_all_admin_users() -> list[dict[str, str]]:
    results = await fetch_all(
        f"""
SELECT * FROM public.{TB_ADMIN_USERS};
""",
    )
    return [
        {"username": result.get("name"), "email": result.get("email"), "jwt_token": result.get("jwt_token")}
        for result in results
    ]


async def create_initial_admin_user():
    if (
        jwt_cfg.admin_token_name
        and jwt_cfg.admin_token_email
        and jwt_cfg.admin_token_password
    ):
        admin_user = await select_admin_user(jwt_cfg.admin_token_email)
        if admin_user is None:
            admin_user = AdminUser(
                name=jwt_cfg.admin_token_name,
                email=jwt_cfg.admin_token_email,
                password_plain=jwt_cfg.admin_token_password,
            )
            await insert_admin_user(admin_user)
    else:
        raise ValueError(
            "ADMIN_TOKEN_NAME, ADMIN_TOKEN_EMAIL and ADMIN_TOKEN_PASSWORD must be set"
        )


async def select_admin_emails() -> list[str]:
    results = await fetch_all(
        f"""
SELECT email FROM public.{TB_ADMIN_USERS};
""",
    )
    return [result.get("email") for result in results]


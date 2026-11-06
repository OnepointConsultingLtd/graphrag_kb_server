from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from graphrag_kb_server.main import multi_tennant_server
from graphrag_kb_server.main.multi_tennant_server import (
    PROJECT_SETTINGS_PATH,
    UNAUTHORIZED,
    WRITE_METHODS,
    auth_middleware,
)

PROTECTED_PATH = "/protected/project/files"


ADMIN_EMAIL = "admin@example.com"


async def call_middleware(
    method: str,
    path: str,
    permissions: list[str],
    email: str = "user@example.com",
):
    """Runs the auth middleware with a token carrying the given permissions and email.

    ADMIN_EMAIL is the only administrator. Returns the response and the mocked downstream handler.
    """
    handler = AsyncMock(return_value=web.json_response({"ok": True}))
    token_data = {"email": email, "permissions": permissions}
    request = make_mocked_request(method, path)
    with patch.object(
        multi_tennant_server, "authenticate_request", AsyncMock(return_value=token_data)
    ), patch.object(
        multi_tennant_server.admin_cfg,
        "get_administrators",
        AsyncMock(return_value=[ADMIN_EMAIL]),
    ):
        response = await auth_middleware(request, handler)
    return response, handler


def test_write_methods_include_put():
    assert {"POST", "PUT", "PATCH", "DELETE"} <= set(WRITE_METHODS)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_read_only_token_cannot_use_write_methods(method):
    response, handler = await call_middleware(method, PROTECTED_PATH, ["read"])
    assert response.status == UNAUTHORIZED
    handler.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_write_token_can_use_write_methods(method):
    response, handler = await call_middleware(method, PROTECTED_PATH, ["read", "write"])
    assert response.status == 200
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_read_only_token_can_use_get():
    response, handler = await call_middleware("GET", PROTECTED_PATH, ["read"])
    assert response.status == 200
    handler.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_project_settings_are_closed_to_non_administrators(method):
    response, handler = await call_middleware(
        method, PROJECT_SETTINGS_PATH, ["read", "write"]
    )
    assert response.status == UNAUTHORIZED
    handler.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_project_settings_are_open_to_administrators_with_the_needed_permission(
    method,
):
    response, handler = await call_middleware(
        method, PROJECT_SETTINGS_PATH, ["read", "write"], email=ADMIN_EMAIL
    )
    assert response.status == 200
    handler.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
async def test_read_only_administrator_cannot_change_project_settings(method):
    response, handler = await call_middleware(
        method, PROJECT_SETTINGS_PATH, ["read"], email=ADMIN_EMAIL
    )
    assert response.status == UNAUTHORIZED
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_read_only_administrator_can_read_project_settings():
    response, handler = await call_middleware(
        "GET", PROJECT_SETTINGS_PATH, ["read"], email=ADMIN_EMAIL
    )
    assert response.status == 200
    handler.assert_called_once()

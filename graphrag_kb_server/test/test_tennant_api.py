import pytest
from aiohttp import web
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient
from graphrag_kb_server.main.multi_tennant_server import routes
from graphrag_kb_server.model.jwt_token import JWTToken
from graphrag_kb_server.model.error import Error, ErrorCode


@pytest.fixture
def test_app():
    """Fixture to set up the aiohttp app for testing."""
    app = web.Application()
    app.add_routes(routes)
    return app


@pytest.mark.asyncio
async def test_create_tennant_success(test_app, aiohttp_client):
    """Test the successful creation of a tennant."""
    test_email = "test@example.com"
    test_folder_name = "test_tennant_folder"
    mock_generate_token = AsyncMock(
        return_value=JWTToken(
            email=test_email, token="test.jwt.token", folder_name=test_folder_name
        )
    )

    with patch(
        "graphrag_kb_server.main.multi_tennant_server.generate_token",
        mock_generate_token,
    ):
        client: TestClient = await aiohttp_client(test_app)
        # Define the request payload
        payload = {"email": test_email, "tennant_name": test_folder_name}

        # Make the POST request
        response = await client.post("/create_tennant", json=payload)

        assert response.status == 200
        data = await response.json()
        assert data["email"] == test_email


@pytest.mark.asyncio
async def test_create_tennant_error(test_app, aiohttp_client):
    expected_error = Error(
        error_code=ErrorCode.TENNANT_EXISTS,
        error="Tennant exists",
        description="The tennant already exists",
    )
    mock_generate_error = AsyncMock(return_value=expected_error)

    with patch(
        "graphrag_kb_server.main.multi_tennant_server.generate_token",
        mock_generate_error,
    ):
        client: TestClient = await aiohttp_client(test_app)
        payload = {"email": "dummy@test.com", "tennant_name": "dummy"}
        # Make the POST request
        response = await client.post("/create_tennant", json=payload)
        assert response.status == 400
        data = await response.json()
        assert data["error"] == expected_error.error

"""End to end tests of the project settings endpoints.

The requests go through the real routes and the Swagger validation; only the database layer is
replaced by an in-memory store (which, like the real one, encrypts secrets).
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo

from graphrag_kb_server.config import cfg
from graphrag_kb_server.main.multi_tennant_server import (
    PROJECT_SETTINGS_PATH,
    TOKEN_DATA,
)
from graphrag_kb_server.main.project_settings_server import routes
from graphrag_kb_server.model.project_setting import SECRET_SETTINGS, ProjectSetting
from graphrag_kb_server.service import project_config_service, project_settings_service
from graphrag_kb_server.service.crypto.secret_cipher import (
    ENCRYPTION_KEY_ENV_VARIABLE,
    encrypt_secret,
    generate_encryption_key,
)

TENNANT = "tennant_a"
PROJECT = "my_project"
URL = f"{PROJECT_SETTINGS_PATH}?project={PROJECT}"
CONFIG_MODULE = "graphrag_kb_server.service.project_config_service"
SETTINGS_MODULE = "graphrag_kb_server.service.project_settings_service"
AUTH_HEADERS = {"Authorization": "Bearer test"}
SMALL = "text-embedding-3-small"
LARGE = "text-embedding-3-large"


class InMemoryStore:
    """Stands in for TB_PROJECT_KEYS. Secrets are encrypted on write like in the real table."""

    def __init__(self):
        self.rows: dict[ProjectSetting, str] = {}

    async def find(self, schema_name, project_id):
        return dict(self.rows)

    async def upsert(self, schema_name, project_id, values):
        for setting, value in values.items():
            if value is None:
                self.rows.pop(setting, None)
            else:
                if setting in SECRET_SETTINGS:
                    encrypt_secret(value)  # fails without encryption key, like the real one
                self.rows[setting] = value

    async def delete(self, schema_name, project_id):
        self.rows.clear()


def create_app() -> web.Application:
    @web.middleware
    async def fake_auth_middleware(request: web.Request, handler):
        request[TOKEN_DATA] = {"sub": TENNANT}
        return await handler(request)

    app = web.Application(middlewares=[fake_auth_middleware])
    swagger = SwaggerDocs(
        app,
        info=SwaggerInfo(title="test", version="1.0.0"),
        security=cfg.config_dir / "security.yaml",
    )
    swagger.add_routes(routes)
    return app


@pytest.fixture
def project_dir(tmp_path: Path):
    directory = tmp_path / TENNANT / "lightrag" / PROJECT
    directory.mkdir(parents=True)
    with patch.object(cfg, "graphrag_root_dir_path", tmp_path):
        yield directory


@pytest.fixture
def store(monkeypatch) -> InMemoryStore:
    monkeypatch.setenv(ENCRYPTION_KEY_ENV_VARIABLE, generate_encryption_key())
    fake = InMemoryStore()
    monkeypatch.setattr(f"{CONFIG_MODULE}.get_project_id", AsyncMock(return_value=1))
    monkeypatch.setattr(f"{SETTINGS_MODULE}.get_project_id", AsyncMock(return_value=1))
    monkeypatch.setattr(f"{CONFIG_MODULE}.find_project_keys", fake.find)
    monkeypatch.setattr(f"{CONFIG_MODULE}.upsert_project_keys", fake.upsert)
    monkeypatch.setattr(f"{CONFIG_MODULE}.delete_project_keys", fake.delete)
    project_config_service.invalidate_project_config_cache()
    yield fake
    project_config_service.invalidate_project_config_cache()


@pytest_asyncio.fixture
async def client(aiohttp_client, project_dir, store):
    return await aiohttp_client(create_app(), headers=AUTH_HEADERS)


def settings_by_name(body: dict) -> dict:
    return {setting["name"]: setting for setting in body["settings"]}


@pytest.mark.asyncio
async def test_get_returns_all_settings_with_masked_secrets(client):
    response = await client.get(URL)
    assert response.status == 200
    body = await response.json()
    assert body["project"] == PROJECT
    assert body["engine"] == "lightrag"
    settings = settings_by_name(body)
    assert set(settings) == {setting.value for setting in ProjectSetting}
    assert all(setting["source"] == "env" for setting in settings.values())
    assert settings["OPENAI_API_KEY"]["secret"] is True
    assert settings["OPENAI_API_KEY"]["value"] in (None, project_settings_service.MASKED_ENV_SECRET)
    assert cfg.openai_api_key not in (await response.text()) or cfg.openai_api_key == ""


@pytest.mark.asyncio
async def test_patch_sets_values_and_masks_the_secret_in_the_response(client):
    response = await client.patch(
        URL,
        json={
            "settings": {
                "LIGHTRAG_MODEL": "gpt-4o",
                "OPENAI_API_KEY": "sk-1234567890abcd",
            }
        },
    )
    assert response.status == 200
    text = await response.text()
    assert "sk-1234567890abcd" not in text
    settings = settings_by_name(await response.json())
    assert settings["LIGHTRAG_MODEL"]["value"] == "gpt-4o"
    assert settings["LIGHTRAG_MODEL"]["source"] == "project"
    assert settings["OPENAI_API_KEY"]["value"].endswith("abcd")
    assert settings["OPENAI_API_KEY"]["source"] == "project"

    again = settings_by_name(await (await client.get(URL)).json())
    assert again["LIGHTRAG_MODEL"]["value"] == "gpt-4o"


@pytest.mark.asyncio
async def test_patch_null_resets_a_setting_to_the_env_value(client):
    await client.patch(URL, json={"settings": {"CAG_MODEL": "mine"}})
    response = await client.patch(URL, json={"settings": {"CAG_MODEL": None}})
    assert response.status == 200
    setting = settings_by_name(await response.json())["CAG_MODEL"]
    assert setting["source"] == "env"
    assert setting["value"] != "mine"


@pytest.mark.asyncio
async def test_patch_invalidates_the_runtime_caches(client, project_dir, monkeypatch):
    called_with = []
    monkeypatch.setattr(
        project_config_service, "_runtime_cache_invalidators", [called_with.append]
    )
    await client.patch(URL, json={"settings": {"CAG_MODEL": "mine"}})
    assert called_with == [project_dir]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"settings": {"LIGHTRAG_MODEL_TYPE": "bogus"}},
        {"settings": {"NOT_A_SETTING": "x"}},
        {"settings": {}},
        {"settings": {"CAG_MODEL": ""}},
        {"settings": {"CAG_MODEL": 5}},
        {"settings": {"OPENAI_API_MODEL_EMBEDDING": "unknown-model"}},
        {"other": {}},
        [],
    ],
)
async def test_patch_rejects_invalid_requests(client, store, body):
    response = await client.patch(URL, json=body)
    assert response.status == 400
    assert store.rows == {}


@pytest.mark.asyncio
async def test_patch_of_a_secret_without_encryption_key_is_service_unavailable(
    client, store, monkeypatch
):
    monkeypatch.delenv(ENCRYPTION_KEY_ENV_VARIABLE)
    response = await client.patch(URL, json={"settings": {"OPENAI_API_KEY": "sk-x"}})
    assert response.status == 503
    assert ENCRYPTION_KEY_ENV_VARIABLE in (await response.text())
    assert store.rows == {}


@pytest.mark.asyncio
async def test_patch_of_a_model_works_without_encryption_key(client, monkeypatch):
    monkeypatch.delenv(ENCRYPTION_KEY_ENV_VARIABLE)
    response = await client.patch(URL, json={"settings": {"CAG_MODEL": "mine"}})
    assert response.status == 200


@pytest.mark.asyncio
async def test_patch_of_a_project_missing_in_the_database_is_not_found(client, monkeypatch):
    monkeypatch.setattr(
        f"{SETTINGS_MODULE}.get_project_id", AsyncMock(side_effect=ValueError("not found"))
    )
    response = await client.patch(URL, json={"settings": {"CAG_MODEL": "mine"}})
    assert response.status == 404


@pytest.mark.asyncio
async def test_embedding_model_of_an_indexed_project_cannot_change(client, project_dir, store):
    (project_dir / "lightrag").mkdir()
    (project_dir / "lightrag" / "vdb_chunks.json").write_text("{}", encoding="utf-8")
    current = (await (await client.get(URL)).json())
    current_model = settings_by_name(current)["OPENAI_API_MODEL_EMBEDDING"]["value"]
    other_model = LARGE if current_model != LARGE else SMALL

    response = await client.patch(
        URL, json={"settings": {"OPENAI_API_MODEL_EMBEDDING": other_model}}
    )
    assert response.status == 409
    assert store.rows == {}

    same = await client.patch(
        URL, json={"settings": {"OPENAI_API_MODEL_EMBEDDING": current_model}}
    )
    assert same.status == 200


@pytest.mark.asyncio
async def test_embedding_model_can_change_before_the_project_is_indexed(client):
    response = await client.patch(
        URL, json={"settings": {"OPENAI_API_MODEL_EMBEDDING": LARGE}}
    )
    assert response.status == 200


@pytest.mark.asyncio
async def test_delete_removes_all_settings(client, store):
    await client.patch(URL, json={"settings": {"CAG_MODEL": "mine", "AUDIO_MODEL": "a"}})
    response = await client.delete(URL)
    assert response.status == 200
    assert store.rows == {}
    assert all(
        setting["source"] == "env"
        for setting in settings_by_name(await response.json()).values()
    )


@pytest.mark.asyncio
async def test_delete_is_blocked_when_it_would_change_the_embedding_model_of_an_index(
    client, project_dir, store
):
    current = settings_by_name(await (await client.get(URL)).json())
    env_model = current["OPENAI_API_MODEL_EMBEDDING"]["value"]
    other_model = LARGE if env_model != LARGE else SMALL
    await client.patch(URL, json={"settings": {"OPENAI_API_MODEL_EMBEDDING": other_model}})
    (project_dir / "lightrag").mkdir()
    (project_dir / "lightrag" / "vdb_chunks.json").write_text("{}", encoding="utf-8")

    response = await client.delete(URL)

    assert response.status == 409
    assert ProjectSetting.OPENAI_API_MODEL_EMBEDDING in store.rows


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
async def test_a_missing_project_parameter_is_a_bad_request(client, method):
    kwargs = {"json": {"settings": {"CAG_MODEL": "x"}}} if method == "patch" else {}
    response = await getattr(client, method)(PROJECT_SETTINGS_PATH, **kwargs)
    assert response.status == 400


@pytest.mark.asyncio
async def test_an_unknown_project_is_a_bad_request_and_creates_no_folder(client, project_dir):
    for method in ("get", "delete"):
        response = await getattr(client, method)(
            f"{PROJECT_SETTINGS_PATH}?project=does_not_exist"
        )
        assert response.status == 400
    response = await client.patch(
        f"{PROJECT_SETTINGS_PATH}?project=does_not_exist",
        json={"settings": {"CAG_MODEL": "x"}},
    )
    assert response.status == 400
    assert not (project_dir.parent / "does_not_exist").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("project", ["..", "../other", "a/b", "..%2F..%2Fetc"])
async def test_a_project_name_with_a_path_is_rejected(client, project, project_dir):
    (project_dir.parent.parent / "other" / "lightrag").mkdir(parents=True)
    response = await client.get(f"{PROJECT_SETTINGS_PATH}?project={project}")
    assert response.status == 400


@pytest.mark.asyncio
async def test_options_is_accepted(client):
    response = await client.options(PROJECT_SETTINGS_PATH)
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_reports_a_missing_encryption_key_when_secrets_are_stored(
    client, store, monkeypatch
):
    """Stored secrets cannot be decrypted without the key: report it instead of failing silently."""
    await client.patch(URL, json={"settings": {"OPENAI_API_KEY": "sk-1234567890abcd"}})

    async def failing_find(schema_name, project_id):
        from graphrag_kb_server.service.crypto.secret_cipher import SecretCipherError

        raise SecretCipherError("PROJECT_KEYS_ENCRYPTION_KEY is not set.")

    monkeypatch.setattr(f"{CONFIG_MODULE}.find_project_keys", failing_find)
    project_config_service.invalidate_project_config_cache()
    response = await client.get(URL)
    assert response.status == 503


@pytest.mark.asyncio
async def test_delete_reports_a_missing_encryption_key_when_secrets_are_stored(
    client, monkeypatch
):
    """DELETE reads the stored settings to protect the embedding model, which needs the key."""
    from graphrag_kb_server.service.crypto.secret_cipher import SecretCipherError

    async def failing_find(schema_name, project_id):
        raise SecretCipherError("PROJECT_KEYS_ENCRYPTION_KEY is not set.")

    monkeypatch.setattr(f"{CONFIG_MODULE}.find_project_keys", failing_find)
    project_config_service.invalidate_project_config_cache()
    response = await client.delete(URL)
    assert response.status == 503

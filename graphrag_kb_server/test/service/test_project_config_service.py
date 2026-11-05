import pytest

from graphrag_kb_server.config import cag_cfg, cfg, lightrag_cfg
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import SimpleProject
from graphrag_kb_server.model.project_setting import ProjectSetting
from graphrag_kb_server.service import project_config_service as service


@pytest.fixture
def project() -> SimpleProject:
    return SimpleProject(
        schema_name="test_schema", engine=Engine.LIGHTRAG, project_name="p1"
    )


class FakeStore:
    """Replaces the database layer and counts reads."""

    def __init__(self, stored: dict[ProjectSetting, str]):
        self.stored = stored
        self.reads = 0
        self.saved: list[dict] = []

    async def find(self, schema_name, project_id):
        self.reads += 1
        return dict(self.stored)

    async def upsert(self, schema_name, project_id, values):
        self.saved.append(values)
        for setting, value in values.items():
            if value is None:
                self.stored.pop(setting, None)
            else:
                self.stored[setting] = value

    async def delete(self, schema_name, project_id):
        self.stored.clear()


@pytest.fixture
def store(monkeypatch) -> FakeStore:
    fake = FakeStore({})

    async def fake_get_project_id(schema_name, project_name, engine, *args, **kwargs):
        return 1

    monkeypatch.setattr(service, "get_project_id", fake_get_project_id)
    monkeypatch.setattr(service, "find_project_keys", fake.find)
    monkeypatch.setattr(service, "upsert_project_keys", fake.upsert)
    monkeypatch.setattr(service, "delete_project_keys", fake.delete)
    service.invalidate_project_config_cache()
    yield fake
    service.invalidate_project_config_cache()


@pytest.mark.asyncio
async def test_fallback_to_env_when_no_row(store, project):
    assert (
        await service.get_project_setting(project, ProjectSetting.OPENAI_API_KEY)
        == cfg.openai_api_key
    )
    assert (
        await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
        == cag_cfg.cag_model
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("setting", list(ProjectSetting))
async def test_env_fallback_for_every_setting(store, project, setting):
    assert await service.get_project_setting(
        project, setting
    ) == service.get_env_setting(setting)


@pytest.mark.asyncio
async def test_override_wins_and_other_fields_fall_back(store, project):
    store.stored = {ProjectSetting.LIGHTRAG_MODEL: "custom-model"}
    assert (
        await service.get_project_setting(project, ProjectSetting.LIGHTRAG_MODEL)
        == "custom-model"
    )
    assert (
        await service.get_project_setting(project, ProjectSetting.LIGHTRAG_LITE_MODEL)
        == lightrag_cfg.lightrag_lite_model
    )


@pytest.mark.asyncio
async def test_cache_avoids_repeated_database_reads(store, project):
    await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
    await service.get_project_setting(project, ProjectSetting.AUDIO_MODEL)
    await service.get_project_config(project)
    assert store.reads == 1


@pytest.mark.asyncio
async def test_save_invalidates_cache(store, project):
    assert (
        await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
        == cag_cfg.cag_model
    )
    await service.save_project_settings(project, {ProjectSetting.CAG_MODEL: "new"})
    assert await service.get_project_setting(project, ProjectSetting.CAG_MODEL) == "new"


@pytest.mark.asyncio
async def test_remove_invalidates_cache_and_falls_back(store, project):
    await service.save_project_settings(project, {ProjectSetting.CAG_MODEL: "new"})
    assert await service.get_project_setting(project, ProjectSetting.CAG_MODEL) == "new"
    await service.remove_project_settings(project)
    assert (
        await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
        == cag_cfg.cag_model
    )


@pytest.mark.asyncio
async def test_cache_expires_after_ttl(store, project, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("graphrag_kb_server.utils.cache.time.time", lambda: now[0])
    await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
    now[0] += service.PROJECT_CONFIG_CACHE_TTL_SECONDS - 1
    await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
    assert store.reads == 1
    now[0] += 2
    await service.get_project_setting(project, ProjectSetting.CAG_MODEL)
    assert store.reads == 2


@pytest.mark.asyncio
async def test_invalid_model_type_rejected_on_save(store, project):
    with pytest.raises(ValueError, match="LIGHTRAG_MODEL_TYPE"):
        await service.save_project_settings(
            project, {ProjectSetting.LIGHTRAG_MODEL_TYPE: "bogus"}
        )
    assert store.saved == []


@pytest.mark.asyncio
async def test_valid_model_type_saved(store, project):
    await service.save_project_settings(
        project, {ProjectSetting.LIGHTRAG_MODEL_TYPE: "openai"}
    )
    assert (
        await service.get_project_setting(project, ProjectSetting.LIGHTRAG_MODEL_TYPE)
        == "openai"
    )


@pytest.mark.asyncio
async def test_invalid_stored_model_type_falls_back_to_env(store, project):
    store.stored = {ProjectSetting.LIGHTRAG_MODEL_TYPE: "bogus"}
    assert (
        await service.get_project_setting(project, ProjectSetting.LIGHTRAG_MODEL_TYPE)
        == lightrag_cfg.lightrag_model_type
    )


@pytest.mark.asyncio
async def test_get_project_config_resolves_all_fields(store, project):
    store.stored = {ProjectSetting.OPENROUTER_MODEL: "x/y"}
    config = await service.get_project_config(project)
    assert config.openrouter_model == "x/y"
    assert config.openai_api_model == cfg.openai_api_model
    assert config.lightrag_model_type == lightrag_cfg.lightrag_model_type

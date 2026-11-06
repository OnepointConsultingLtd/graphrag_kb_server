from pathlib import Path

import pytest

from graphrag_kb_server.config import cag_cfg, cfg, lightrag_cfg
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import SimpleProject
from graphrag_kb_server.model.project_setting import ProjectSetting, SettingSource
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
    assert config.lightrag_reasoning_effort == lightrag_cfg.lightrag_reasoning_effort


@pytest.mark.asyncio
async def test_reasoning_effort_can_be_overridden_per_project(store, project):
    store.stored = {ProjectSetting.LIGHTRAG_REASONING_EFFORT: "none"}
    config = await service.get_project_config(project)
    assert config.lightrag_reasoning_effort == "none"
    assert (
        config.describe_sources()[ProjectSetting.LIGHTRAG_REASONING_EFFORT]
        == SettingSource.PROJECT
    )


PROJECT_DIR = Path("/root/test_schema/lightrag/p1")


@pytest.mark.asyncio
async def test_get_project_config_for_dir_uses_schema_engine_and_name_from_path(
    store, monkeypatch
):
    seen_projects = []
    original_load = service._load_project_settings

    async def recording_load(project):
        seen_projects.append(project)
        return await original_load(project)

    monkeypatch.setattr(service, "_load_project_settings", recording_load)
    store.stored = {ProjectSetting.CAG_MODEL: "dir-model"}
    config = await service.get_project_config_for_dir(PROJECT_DIR)
    assert config.cag_model == "dir-model"
    assert seen_projects == [
        SimpleProject(
            schema_name="test_schema", engine=Engine.LIGHTRAG, project_name="p1"
        )
    ]


@pytest.mark.asyncio
async def test_describe_sources_reports_project_or_env_without_values(store, project):
    store.stored = {
        ProjectSetting.OPENAI_API_KEY: "sk-secret",
        ProjectSetting.CAG_MODEL: "m",
    }
    sources = (await service.get_project_config(project)).describe_sources()
    assert set(sources) == set(ProjectSetting)
    assert sources[ProjectSetting.OPENAI_API_KEY] == SettingSource.PROJECT
    assert sources[ProjectSetting.CAG_MODEL] == SettingSource.PROJECT
    assert sources[ProjectSetting.GEMINI_API_KEY] == SettingSource.ENV
    assert "sk-secret" not in str(sources)


@pytest.mark.asyncio
async def test_describe_sources_reports_env_for_invalid_stored_value(store, project):
    store.stored = {ProjectSetting.LIGHTRAG_MODEL_TYPE: "bogus"}
    sources = (await service.get_project_config(project)).describe_sources()
    assert sources[ProjectSetting.LIGHTRAG_MODEL_TYPE] == SettingSource.ENV


@pytest.fixture
def isolated_invalidators(monkeypatch) -> list:
    invalidators: list = []
    monkeypatch.setattr(service, "_runtime_cache_invalidators", invalidators)
    return invalidators


def test_invalidate_runtime_caches_calls_registered_invalidators(
    store, isolated_invalidators
):
    called_with = []
    service.register_runtime_cache_invalidator(called_with.append)
    service.register_runtime_cache_invalidator(called_with.append)  # no duplicate
    service.invalidate_project_runtime_caches(PROJECT_DIR)
    assert called_with == [PROJECT_DIR]


def test_failing_invalidator_does_not_stop_the_others(store, isolated_invalidators):
    called_with = []

    def failing_invalidator(project_dir):
        raise RuntimeError("boom")

    service.register_runtime_cache_invalidator(failing_invalidator)
    service.register_runtime_cache_invalidator(called_with.append)
    service.invalidate_project_runtime_caches(PROJECT_DIR)
    assert called_with == [PROJECT_DIR]


@pytest.mark.asyncio
async def test_invalidate_runtime_caches_drops_cached_settings(
    store, project, isolated_invalidators
):
    await service.get_project_config_for_dir(PROJECT_DIR)
    await service.get_project_config_for_dir(PROJECT_DIR)
    assert store.reads == 1
    service.invalidate_project_runtime_caches(PROJECT_DIR)
    await service.get_project_config_for_dir(PROJECT_DIR)
    assert store.reads == 2


def test_lightrag_and_cag_caches_are_registered_and_cleared(store):
    from graphrag_kb_server.service.cag.cag_support import (
        CHAT_CACHE,
        _chat_cache_key,
    )
    from graphrag_kb_server.service.lightrag.lightrag_init import lightrag_cache

    other_dir = Path("/root/test_schema/lightrag/other")
    lightrag_cache.set(PROJECT_DIR, "rag-p1")
    lightrag_cache.set(other_dir, "rag-other")
    CHAT_CACHE.set(_chat_cache_key(PROJECT_DIR, "c1"), "chat-p1")
    CHAT_CACHE.set(_chat_cache_key(other_dir, "c1"), "chat-other")
    try:
        service.invalidate_project_runtime_caches(PROJECT_DIR)
        assert lightrag_cache.get(PROJECT_DIR) is None
        assert CHAT_CACHE.get(_chat_cache_key(PROJECT_DIR, "c1")) is None
        assert lightrag_cache.get(other_dir) == "rag-other"
        assert CHAT_CACHE.get(_chat_cache_key(other_dir, "c1")) == "chat-other"
    finally:
        lightrag_cache.clear(other_dir)
        CHAT_CACHE.invalidate(_chat_cache_key(other_dir, "c1"))


def test_from_env_has_exactly_the_env_values_and_no_overrides():
    config = service.ProjectConfig.from_env()
    for setting in ProjectSetting:
        assert getattr(config, setting.value.lower()) == service.get_env_setting(setting)
    assert config.overridden_settings == frozenset()
    assert config.project_label == ""
    assert set(config.describe_sources().values()) == {SettingSource.ENV}


@pytest.mark.asyncio
async def test_project_config_carries_a_label_for_log_lines(store, project):
    config = await service.get_project_config(project)
    assert config.project_label == "test_schema/p1"


@pytest.mark.asyncio
async def test_project_missing_in_database_falls_back_to_env_without_caching(
    store, project, monkeypatch
):
    calls = []

    async def missing_project_id(schema_name, project_name, engine, *args, **kwargs):
        calls.append(project_name)
        raise ValueError("Project p1 with engine lightrag not found")

    monkeypatch.setattr(service, "get_project_id", missing_project_id)
    config = await service.get_project_config(project)
    assert config.cag_model == cag_cfg.cag_model
    assert config.overridden_settings == frozenset()
    # Not cached: the project may be created right after and must then be looked up again.
    await service.get_project_config(project)
    assert len(calls) == 2
    assert store.reads == 0

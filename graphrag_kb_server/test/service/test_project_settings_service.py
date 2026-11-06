from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from graphrag_kb_server.model.project_setting import (
    SECRET_SETTINGS,
    ProjectSetting,
    SettingSource,
)
from graphrag_kb_server.service import project_settings_service as service
from graphrag_kb_server.service.project_config_service import (
    ProjectConfig,
    get_env_setting,
)

MODULE = "graphrag_kb_server.service.project_settings_service"
SMALL = "text-embedding-3-small"
LARGE = "text-embedding-3-large"


def make_config(overridden=(), **values) -> ProjectConfig:
    return replace(
        ProjectConfig.from_env(),
        overridden_settings=frozenset(overridden),
        project_label="tenant/project",
        **values,
    )


# --- build_settings_view ------------------------------------------------------


def test_view_lists_every_setting_in_order():
    view = service.build_settings_view(make_config())
    assert [setting.name for setting in view] == [s.value for s in ProjectSetting]
    assert {setting.name for setting in view if setting.secret} == {
        s.value for s in SECRET_SETTINGS
    }


def test_view_masks_project_secrets_down_to_the_last_characters():
    config = make_config(
        overridden=[ProjectSetting.OPENAI_API_KEY], openai_api_key="sk-1234567890abcd"
    )
    setting = _find(service.build_settings_view(config), "OPENAI_API_KEY")
    assert setting.value == "*" * 13 + "abcd"
    assert setting.source == SettingSource.PROJECT


def test_view_never_reveals_secrets_from_env():
    config = make_config(gemini_api_key="global-gemini-key-1234")
    setting = _find(service.build_settings_view(config), "GEMINI_API_KEY")
    assert setting.value == service.MASKED_ENV_SECRET
    assert setting.source == SettingSource.ENV
    assert "global-gemini" not in setting.model_dump_json()


def test_view_shows_none_for_a_secret_which_is_not_configured():
    config = make_config(openrouter_api_key="")
    assert _find(service.build_settings_view(config), "OPENROUTER_API_KEY").value is None


def test_view_shows_models_in_clear_with_their_source():
    config = make_config(overridden=[ProjectSetting.CAG_MODEL], cag_model="my-model")
    views = service.build_settings_view(config)
    assert _find(views, "CAG_MODEL").value == "my-model"
    assert _find(views, "CAG_MODEL").source == SettingSource.PROJECT
    assert _find(views, "LIGHTRAG_MODEL").source == SettingSource.ENV


def _find(views, name):
    return next(view for view in views if view.name == name)


# --- parse_settings_update ----------------------------------------------------


def test_parse_accepts_values_and_null():
    parsed = service.parse_settings_update(
        {"settings": {"LIGHTRAG_MODEL": "gpt-4o", "CAG_MODEL": None}}
    )
    assert parsed == {
        ProjectSetting.LIGHTRAG_MODEL: "gpt-4o",
        ProjectSetting.CAG_MODEL: None,
    }


def test_parse_strips_whitespace_around_values():
    parsed = service.parse_settings_update({"settings": {"OPENAI_API_KEY": "  sk-1 \n"}})
    assert parsed == {ProjectSetting.OPENAI_API_KEY: "sk-1"}


@pytest.mark.parametrize(
    "body",
    [None, [], "x", {}, {"settings": None}, {"settings": []}, {"settings": {}}],
)
def test_parse_rejects_malformed_bodies(body):
    with pytest.raises(ValueError):
        service.parse_settings_update(body)


def test_parse_rejects_unknown_settings_and_lists_them():
    with pytest.raises(ValueError, match="Unknown settings: BOGUS, OTHER"):
        service.parse_settings_update(
            {"settings": {"BOGUS": "x", "OTHER": "y", "CAG_MODEL": "m"}}
        )


@pytest.mark.parametrize("value", ["", "   ", 5, True, ["a"], {"a": 1}])
def test_parse_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="CAG_MODEL"):
        service.parse_settings_update({"settings": {"CAG_MODEL": value}})


def test_parse_rejects_unsupported_embedding_model_but_accepts_supported_ones():
    with pytest.raises(ValueError, match="Unsupported embedding model"):
        service.parse_settings_update({"settings": {"OPENAI_API_MODEL_EMBEDDING": "nope"}})
    assert service.parse_settings_update(
        {"settings": {"OPENAI_API_MODEL_EMBEDDING": LARGE}}
    ) == {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: LARGE}
    assert service.parse_settings_update(
        {"settings": {"OPENAI_API_MODEL_EMBEDDING": None}}
    ) == {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: None}


# --- apply / clear ------------------------------------------------------------


def make_project_dir(root: Path, engine: str = "lightrag", with_vectors: bool = False) -> Path:
    project_dir = root / "tenant" / engine / "project"
    (project_dir / "lightrag").mkdir(parents=True)
    if with_vectors:
        (project_dir / "lightrag" / "vdb_chunks.json").write_text("{}", encoding="utf-8")
    return project_dir


@pytest.fixture
def collaborators(monkeypatch):
    """Replaces the database and the cache invalidation; the current embedding model is SMALL."""
    mocks = type("Mocks", (), {})()
    mocks.get_project_id = AsyncMock(return_value=1)
    mocks.save = AsyncMock()
    mocks.remove = AsyncMock()
    mocks.invalidate = Mock()
    mocks.current_config = make_config(openai_api_model_embedding=SMALL)
    monkeypatch.setattr(f"{MODULE}.get_project_id", mocks.get_project_id)
    monkeypatch.setattr(f"{MODULE}.save_project_settings", mocks.save)
    monkeypatch.setattr(f"{MODULE}.remove_project_settings", mocks.remove)
    monkeypatch.setattr(f"{MODULE}.invalidate_project_runtime_caches", mocks.invalidate)
    monkeypatch.setattr(
        f"{MODULE}.get_project_config_for_dir",
        AsyncMock(side_effect=lambda project_dir: mocks.current_config),
    )
    return mocks


@pytest.mark.asyncio
async def test_apply_saves_and_invalidates_the_runtime_caches(tmp_path, collaborators):
    project_dir = make_project_dir(tmp_path)
    values = {ProjectSetting.LIGHTRAG_MODEL: "gpt-4o"}

    await service.apply_settings_update(project_dir, values)

    assert collaborators.save.call_args.args[1] == values
    collaborators.invalidate.assert_called_once_with(project_dir)


@pytest.mark.asyncio
async def test_apply_rejects_a_project_which_is_not_in_the_database(tmp_path, collaborators):
    collaborators.get_project_id.side_effect = ValueError("not found")
    with pytest.raises(service.ProjectNotInDatabaseError):
        await service.apply_settings_update(
            make_project_dir(tmp_path), {ProjectSetting.CAG_MODEL: "m"}
        )
    collaborators.save.assert_not_awaited()
    collaborators.invalidate.assert_not_called()


@pytest.mark.asyncio
async def test_apply_blocks_an_embedding_model_change_on_an_indexed_project(
    tmp_path, collaborators
):
    project_dir = make_project_dir(tmp_path, with_vectors=True)
    with pytest.raises(service.EmbeddingModelLockedError, match=SMALL):
        await service.apply_settings_update(
            project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: LARGE}
        )
    collaborators.save.assert_not_awaited()
    collaborators.invalidate.assert_not_called()


@pytest.mark.asyncio
async def test_apply_allows_setting_the_embedding_model_it_already_has(tmp_path, collaborators):
    project_dir = make_project_dir(tmp_path, with_vectors=True)
    await service.apply_settings_update(
        project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: SMALL}
    )
    collaborators.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_allows_an_embedding_model_change_before_the_first_indexing(
    tmp_path, collaborators
):
    project_dir = make_project_dir(tmp_path, with_vectors=False)
    await service.apply_settings_update(
        project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: LARGE}
    )
    collaborators.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_ignores_the_embedding_guard_for_cag_projects(tmp_path, collaborators):
    project_dir = make_project_dir(tmp_path, engine="cag", with_vectors=True)
    await service.apply_settings_update(
        project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: LARGE}
    )
    collaborators.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_resetting_the_embedding_model_is_compared_with_the_env_value(
    tmp_path, collaborators
):
    """Resetting to .env changes the model when the project overrides it with another one."""
    project_dir = make_project_dir(tmp_path, with_vectors=True)
    env_model = get_env_setting(ProjectSetting.OPENAI_API_MODEL_EMBEDDING)
    other_model = LARGE if env_model != LARGE else SMALL
    collaborators.current_config = make_config(openai_api_model_embedding=other_model)
    with pytest.raises(service.EmbeddingModelLockedError):
        await service.apply_settings_update(
            project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: None}
        )

    collaborators.current_config = make_config(openai_api_model_embedding=env_model)
    await service.apply_settings_update(
        project_dir, {ProjectSetting.OPENAI_API_MODEL_EMBEDDING: None}
    )
    collaborators.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_removes_the_settings_and_invalidates(tmp_path, collaborators):
    project_dir = make_project_dir(tmp_path, with_vectors=True)
    collaborators.current_config = make_config(
        openai_api_model_embedding=get_env_setting(ProjectSetting.OPENAI_API_MODEL_EMBEDDING)
    )
    await service.clear_project_settings(project_dir)
    collaborators.remove.assert_awaited_once()
    collaborators.invalidate.assert_called_once_with(project_dir)


@pytest.mark.asyncio
async def test_clear_is_blocked_when_it_would_change_the_embedding_model_of_an_index(
    tmp_path, collaborators
):
    project_dir = make_project_dir(tmp_path, with_vectors=True)
    env_model = get_env_setting(ProjectSetting.OPENAI_API_MODEL_EMBEDDING)
    collaborators.current_config = make_config(
        openai_api_model_embedding=LARGE if env_model != LARGE else SMALL
    )
    with pytest.raises(service.EmbeddingModelLockedError):
        await service.clear_project_settings(project_dir)
    collaborators.remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_of_a_project_which_is_not_in_the_database(tmp_path, collaborators):
    collaborators.get_project_id.side_effect = ValueError("not found")
    with pytest.raises(service.ProjectNotInDatabaseError):
        await service.clear_project_settings(make_project_dir(tmp_path))

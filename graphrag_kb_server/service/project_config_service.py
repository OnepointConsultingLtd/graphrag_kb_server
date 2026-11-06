"""Per-project configuration lookup.

Resolution rule: a value stored in TB_PROJECT_KEYS for the project wins, otherwise the value
from the ``.env`` based configuration objects is used.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from graphrag_kb_server.config import LightRAGModelType, cag_cfg, cfg, lightrag_cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.project import SimpleProject
from graphrag_kb_server.model.project_setting import ProjectSetting, SettingSource
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id,
)
from graphrag_kb_server.service.db.db_persistence_project_keys import (
    delete_project_keys,
    find_project_keys,
    upsert_project_keys,
)
from graphrag_kb_server.utils.cache import GenericSimpleCache

PROJECT_CONFIG_CACHE_TTL_SECONDS = 60

# The single place which knows where the .env fallback of each setting lives.
_ENV_FALLBACK_SOURCES: dict[ProjectSetting, tuple[object, str]] = {
    ProjectSetting.OPENAI_API_KEY: (cfg, "openai_api_key"),
    ProjectSetting.OPENAI_API_MODEL: (cfg, "openai_api_model"),
    ProjectSetting.OPENAI_API_MODEL_EMBEDDING: (cfg, "openai_api_model_embedding"),
    ProjectSetting.AUDIO_MODEL: (cfg, "audio_model"),
    ProjectSetting.GEMINI_API_KEY: (cfg, "gemini_api_key"),
    ProjectSetting.OPENROUTER_API_KEY: (cfg, "openrouter_api_key"),
    ProjectSetting.OPENROUTER_MODEL: (cfg, "openrouter_model"),
    ProjectSetting.OPENROUTER_PROVIDER: (cfg, "openrouter_provider"),
    ProjectSetting.TOGETHERAI_API_KEY: (cfg, "togetherai_api_key"),
    ProjectSetting.LIGHTRAG_MODEL: (lightrag_cfg, "lightrag_model"),
    ProjectSetting.LIGHTRAG_LITE_MODEL: (lightrag_cfg, "lightrag_lite_model"),
    ProjectSetting.LIGHTRAG_MODEL_TYPE: (lightrag_cfg, "lightrag_model_type"),
    ProjectSetting.LIGHTRAG_REASONING_EFFORT: (
        lightrag_cfg,
        "lightrag_reasoning_effort",
    ),
    ProjectSetting.CAG_MODEL: (cag_cfg, "cag_model"),
}

ProjectCacheKey = tuple[str, str, str]

# Caches the whole decrypted row per project. An empty dict means "no row" (negative result).
_project_settings_cache: GenericSimpleCache[
    dict[ProjectSetting, str], ProjectCacheKey
] = GenericSimpleCache(timeout=PROJECT_CONFIG_CACHE_TTL_SECONDS)


@dataclass(frozen=True)
class ProjectConfig:
    """All per-project settings, already resolved against the .env fallbacks."""

    openai_api_key: str | None
    openai_api_model: str | None
    openai_api_model_embedding: str | None
    audio_model: str | None
    gemini_api_key: str | None
    openrouter_api_key: str | None
    openrouter_model: str | None
    openrouter_provider: str | None
    togetherai_api_key: str | None
    lightrag_model: str | None
    lightrag_lite_model: str | None
    lightrag_model_type: str | None
    lightrag_reasoning_effort: str | None
    cag_model: str | None
    # The settings whose value comes from the project row (all others come from .env).
    overridden_settings: frozenset[ProjectSetting] = field(default_factory=frozenset)
    # "<schema>/<project>", used as a prefix in log lines. Empty when there is no project.
    project_label: str = ""

    @classmethod
    def from_env(cls) -> "ProjectConfig":
        """The configuration without any project override, i.e. exactly the .env values.

        For code paths which are not tied to a project (e.g. scripts, the Vimeo transcription).
        """
        return cls(
            **{
                setting.value.lower(): get_env_setting(setting)
                for setting in ProjectSetting
            }
        )

    def describe_sources(self) -> dict[ProjectSetting, SettingSource]:
        """Return where each setting comes from. Never contains values, so it is safe to log."""
        return {
            setting: (
                SettingSource.PROJECT
                if setting in self.overridden_settings
                else SettingSource.ENV
            )
            for setting in ProjectSetting
        }


def _cache_key(project: SimpleProject) -> ProjectCacheKey:
    return (project.schema_name, project.project_name, project.engine.value)


def get_env_setting(setting: ProjectSetting) -> str | None:
    """Return the .env based value of a setting."""
    source, attribute = _ENV_FALLBACK_SOURCES[setting]
    return getattr(source, attribute)


def validate_project_setting(setting: ProjectSetting, value: str) -> None:
    """Raise ValueError if the value is not acceptable for the setting."""
    if setting == ProjectSetting.LIGHTRAG_MODEL_TYPE and value not in {
        model_type.value for model_type in LightRAGModelType
    }:
        raise ValueError(
            f"Invalid {setting.value} '{value}'. Valid values: "
            f"{', '.join(model_type.value for model_type in LightRAGModelType)}"
        )


async def _load_project_settings(project: SimpleProject) -> dict[ProjectSetting, str]:
    """Return the stored settings of a project, using the TTL cache."""
    key = _cache_key(project)
    cached_settings = _project_settings_cache.get(key)
    if cached_settings is not None:
        return cached_settings
    try:
        project_id = await get_project_id(
            project.schema_name, project.project_name, project.engine.value
        )
    except ValueError:
        # A project which is not in the database (yet) cannot have overrides. This is not
        # cached, so overrides are picked up as soon as the project exists.
        logger.debug(f"Project {project.project_name} is not in the database")
        return {}
    stored_settings = await find_project_keys(project.schema_name, project_id)
    _project_settings_cache.set(key, stored_settings)
    return stored_settings


def _resolve_setting(
    stored_settings: dict[ProjectSetting, str],
    setting: ProjectSetting,
    project: SimpleProject,
) -> tuple[str | None, SettingSource]:
    """Resolve one setting against the stored overrides, returning the value and its source."""
    override = stored_settings.get(setting)
    if override is not None:
        try:
            validate_project_setting(setting, override)
        except ValueError:
            logger.warning(
                f"Ignoring invalid stored {setting.value} for project {project.project_name}"
            )
        else:
            return override, SettingSource.PROJECT
    return get_env_setting(setting), SettingSource.ENV


async def get_project_setting(
    project: SimpleProject, setting: ProjectSetting
) -> str | None:
    """Resolve one setting: the project override if present, otherwise the .env value."""
    stored_settings = await _load_project_settings(project)
    return _resolve_setting(stored_settings, setting, project)[0]


async def get_project_config(project: SimpleProject) -> ProjectConfig:
    """Resolve all settings of a project with a single (cached) database read."""
    stored_settings = await _load_project_settings(project)
    values: dict[str, str | None] = {}
    overridden: set[ProjectSetting] = set()
    for setting in ProjectSetting:
        value, source = _resolve_setting(stored_settings, setting, project)
        values[setting.value.lower()] = value
        if source == SettingSource.PROJECT:
            overridden.add(setting)
    return ProjectConfig(
        **values,
        overridden_settings=frozenset(overridden),
        project_label=f"{project.schema_name}/{project.project_name}",
    )


async def get_project_config_for_dir(project_dir: Path) -> ProjectConfig:
    """Resolve the configuration of the project living in the given project directory
    (``<root>/<schema>/<engine>/<project>``)."""
    return await get_project_config(extract_elements_from_path(project_dir))


def invalidate_project_config_cache(project: SimpleProject | None = None) -> None:
    """Drop the cached settings of one project, or of all projects if none is given."""
    if project is None:
        _project_settings_cache.clear()
    else:
        _project_settings_cache.invalidate(_cache_key(project))


# Callbacks which drop in-process objects built from a project's settings (e.g. LightRAG
# instances, CAG chats). Modules owning such caches register themselves here, so this
# service does not have to import the heavy RAG modules (which would be circular).
_runtime_cache_invalidators: list[Callable[[Path], None]] = []


def register_runtime_cache_invalidator(invalidator: Callable[[Path], None]) -> None:
    """Register a callback receiving the project directory, called when the project's settings
    change. Registering the same callback twice has no effect."""
    if invalidator not in _runtime_cache_invalidators:
        _runtime_cache_invalidators.append(invalidator)


def invalidate_project_runtime_caches(project_dir: Path) -> None:
    """Drop the cached settings of a project and every registered runtime object built from them,
    so the next request uses the current settings. A failing invalidator does not stop the others."""
    invalidate_project_config_cache(extract_elements_from_path(project_dir))
    for invalidator in _runtime_cache_invalidators:
        try:
            invalidator(project_dir)
        except Exception as error:
            logger.error(
                f"Runtime cache invalidation failed for {project_dir.name}: {error}"
            )


async def save_project_settings(
    project: SimpleProject, values: dict[ProjectSetting, str | None]
) -> None:
    """Validate and persist overrides for a project, making them effective immediately.

    A value of None resets that setting to the .env fallback.
    """
    for setting, value in values.items():
        if value is not None:
            validate_project_setting(setting, value)
    project_id = await get_project_id(
        project.schema_name, project.project_name, project.engine.value
    )
    await upsert_project_keys(project.schema_name, project_id, values)
    invalidate_project_config_cache(project)


async def remove_project_settings(project: SimpleProject) -> None:
    """Delete all overrides of a project so it falls back to .env entirely."""
    project_id = await get_project_id(
        project.schema_name, project.project_name, project.engine.value
    )
    await delete_project_keys(project.schema_name, project_id)
    invalidate_project_config_cache(project)

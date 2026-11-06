"""Reading and changing the settings of a project on behalf of the settings endpoint and the CLI.

Builds the API view (secrets masked), validates change requests and applies them: persists the
settings, protects indexed projects from an embedding model change and drops the in-process
objects built from the old settings.
"""

from pathlib import Path

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project_setting import (
    SECRET_SETTINGS,
    ProjectSetting,
    SettingSource,
)
from graphrag_kb_server.model.project_settings_view import (
    ProjectSettingsView,
    ProjectSettingView,
)
from graphrag_kb_server.service.crypto.secret_cipher import mask_secret
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id,
)
from graphrag_kb_server.service.lightrag.lightrag_embedding import (
    get_embedding_dimension,
    project_has_vectors,
)
from graphrag_kb_server.service.project_config_service import (
    ProjectConfig,
    get_env_setting,
    get_project_config,
    get_project_config_for_dir,
    invalidate_project_runtime_caches,
    remove_project_settings,
    save_project_settings,
)

# Shown instead of a secret taken from .env: the project view must never reveal the global keys.
MASKED_ENV_SECRET = "********"


class ProjectNotInDatabaseError(Exception):
    """The project has no row in the projects table, so it cannot have settings."""


class EmbeddingModelLockedError(Exception):
    """The embedding model of an indexed project cannot change: its vectors would no longer match."""


def build_settings_view(config: ProjectConfig) -> list[ProjectSettingView]:
    """The settings of a project for API clients, in the order of ProjectSetting.

    Secrets set by the project are masked down to their last characters; secrets coming from
    .env are fully masked, so the global keys never leave the server.
    """
    sources = config.describe_sources()
    views = []
    for setting in ProjectSetting:
        value = getattr(config, setting.value.lower())
        source = sources[setting]
        is_secret = setting in SECRET_SETTINGS
        if is_secret and value:
            value = (
                mask_secret(value) if source == SettingSource.PROJECT else MASKED_ENV_SECRET
            )
        views.append(
            ProjectSettingView(
                name=setting.value,
                value=value or None,
                source=source,
                secret=is_secret,
            )
        )
    return views


def parse_settings_update(body: object) -> dict[ProjectSetting, str | None]:
    """Validate the body of a change request: ``{"settings": {NAME: value-or-null, ...}}``.

    A string value (surrounding whitespace removed) sets an override, null resets the setting to
    the .env value. Raises ValueError with a message for the client when the body is invalid.
    """
    if not isinstance(body, dict) or not isinstance(body.get("settings"), dict):
        raise ValueError('The body must be an object like {"settings": {"NAME": "value"}}')
    requested = body["settings"]
    if not requested:
        raise ValueError("No settings were specified")
    valid_names = {setting.value for setting in ProjectSetting}
    unknown_names = sorted(str(name) for name in requested if name not in valid_names)
    if unknown_names:
        raise ValueError(
            f"Unknown settings: {', '.join(unknown_names)}. "
            f"Valid settings: {', '.join(sorted(valid_names))}"
        )
    parsed: dict[ProjectSetting, str | None] = {}
    for name, value in requested.items():
        setting = ProjectSetting(name)
        if value is None:
            parsed[setting] = None
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"The value of {name} must be a non-empty string, or null to reset it"
            )
        parsed[setting] = value.strip()
    if ProjectSetting.OPENAI_API_MODEL_EMBEDDING in parsed:
        embedding_model = parsed[ProjectSetting.OPENAI_API_MODEL_EMBEDDING]
        if embedding_model is not None:
            get_embedding_dimension(embedding_model)  # raises ValueError if unsupported
    return parsed


async def get_settings_view(project_dir: Path) -> ProjectSettingsView:
    """The current settings of the project in the given directory."""
    project = extract_elements_from_path(project_dir)
    config = await get_project_config(project)
    return ProjectSettingsView(
        project=project.project_name,
        engine=project.engine.value,
        settings=build_settings_view(config),
    )


async def _ensure_project_in_database(project_dir: Path) -> None:
    project = extract_elements_from_path(project_dir)
    try:
        await get_project_id(
            project.schema_name, project.project_name, project.engine.value
        )
    except ValueError as error:
        raise ProjectNotInDatabaseError(str(error)) from error


async def _ensure_embedding_model_unchanged(
    project_dir: Path, new_embedding_model: str | None
) -> None:
    """Raise EmbeddingModelLockedError if the change would alter the embedding model of a project
    which already has vectors. Only LightRAG projects have embeddings."""
    project = extract_elements_from_path(project_dir)
    if project.engine != Engine.LIGHTRAG or not project_has_vectors(project_dir):
        return
    current_model = (await get_project_config_for_dir(project_dir)).openai_api_model_embedding
    if new_embedding_model != current_model:
        raise EmbeddingModelLockedError(
            f"The project is already indexed with the embedding model {current_model}. "
            f"Changing it to {new_embedding_model} would make the existing vectors unusable; "
            "delete the index first."
        )


async def apply_settings_update(
    project_dir: Path, values: dict[ProjectSetting, str | None]
) -> None:
    """Persist the settings of a project and make them effective immediately.

    Raises ProjectNotInDatabaseError, EmbeddingModelLockedError, or ValueError for an invalid
    value (from the persistence layer) and SecretCipherError when a secret has to be encrypted
    but the encryption key is not configured.
    """
    await _ensure_project_in_database(project_dir)
    if ProjectSetting.OPENAI_API_MODEL_EMBEDDING in values:
        new_model = values[ProjectSetting.OPENAI_API_MODEL_EMBEDDING] or get_env_setting(
            ProjectSetting.OPENAI_API_MODEL_EMBEDDING
        )
        await _ensure_embedding_model_unchanged(project_dir, new_model)
    await save_project_settings(extract_elements_from_path(project_dir), values)
    invalidate_project_runtime_caches(project_dir)


async def clear_project_settings(project_dir: Path) -> None:
    """Remove every override of the project, so it uses the .env values again."""
    await _ensure_project_in_database(project_dir)
    await _ensure_embedding_model_unchanged(
        project_dir, get_env_setting(ProjectSetting.OPENAI_API_MODEL_EMBEDDING)
    )
    await remove_project_settings(extract_elements_from_path(project_dir))
    invalidate_project_runtime_caches(project_dir)

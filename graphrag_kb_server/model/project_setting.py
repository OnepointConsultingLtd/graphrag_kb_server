from enum import StrEnum


class ProjectSetting(StrEnum):
    """Settings that can be overridden per project. The value is both the column name in
    TB_PROJECT_KEYS and the name of the matching ``.env`` variable."""

    OPENAI_API_KEY = "OPENAI_API_KEY"
    OPENAI_API_MODEL = "OPENAI_API_MODEL"
    OPENAI_API_MODEL_EMBEDDING = "OPENAI_API_MODEL_EMBEDDING"
    AUDIO_MODEL = "AUDIO_MODEL"
    GEMINI_API_KEY = "GEMINI_API_KEY"
    OPENROUTER_API_KEY = "OPENROUTER_API_KEY"
    OPENROUTER_MODEL = "OPENROUTER_MODEL"
    OPENROUTER_PROVIDER = "OPENROUTER_PROVIDER"
    TOGETHERAI_API_KEY = "TOGETHERAI_API_KEY"
    LIGHTRAG_MODEL = "LIGHTRAG_MODEL"
    LIGHTRAG_LITE_MODEL = "LIGHTRAG_LITE_MODEL"
    LIGHTRAG_MODEL_TYPE = "LIGHTRAG_MODEL_TYPE"
    LIGHTRAG_REASONING_EFFORT = "LIGHTRAG_REASONING_EFFORT"
    CAG_MODEL = "CAG_MODEL"


class SettingSource(StrEnum):
    """Where the effective value of a setting comes from."""

    PROJECT = "project"
    ENV = "env"


# Settings stored encrypted (Fernet ciphertext) in the database.
SECRET_SETTINGS: frozenset[ProjectSetting] = frozenset(
    {
        ProjectSetting.OPENAI_API_KEY,
        ProjectSetting.GEMINI_API_KEY,
        ProjectSetting.OPENROUTER_API_KEY,
        ProjectSetting.TOGETHERAI_API_KEY,
    }
)

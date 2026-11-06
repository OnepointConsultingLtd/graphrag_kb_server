from pydantic import BaseModel, Field

from graphrag_kb_server.model.project_setting import SettingSource


class ProjectSettingView(BaseModel):
    """One setting of a project as shown to API clients. Secrets are never returned in clear."""

    name: str = Field(..., description="The name of the setting")
    value: str | None = Field(
        default=None,
        description="The effective value. Secrets are masked; None if nothing is configured.",
    )
    source: SettingSource = Field(
        ..., description="Whether the value comes from the project or from the .env file"
    )
    secret: bool = Field(..., description="Whether the setting is a secret (API key)")


class ProjectSettingsView(BaseModel):
    project: str = Field(..., description="The name of the project")
    engine: str = Field(..., description="The engine of the project")
    settings: list[ProjectSettingView] = Field(
        ..., description="All the settings of the project"
    )

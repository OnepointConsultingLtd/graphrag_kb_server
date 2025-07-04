from enum import StrEnum
from pydantic import BaseModel, Field


class WidgetType(StrEnum):
    FLOATING_CHAT = "FLOATING_CHAT"
    CHAT = "CHAT"


class SearchType(StrEnum):
    LOCAL = "local"
    GLOBAL = "global"
    ALL = "all"


class Platform(StrEnum):
    LIGHTRAG = "lightrag"
    GRAPHRAG = "graphrag"


class Project(BaseModel):
    name: str = Field(..., description="The name of the project")
    updated_timestamp: str = Field(
        ..., description="The updated timestamp of the project"
    )
    input_files: list[str] = Field(
        default=[], description="The input files of the project"
    )
    search_type: SearchType = Field(..., description="The type of search to be used")
    platform: Platform = Field(..., description="The platform to be used")
    additional_prompt_instructions: str = Field(
        ..., description="The additional prompt instructions"
    )


class Snippet(BaseModel):
    widget_type: WidgetType = Field(..., description="The type of widget to be used")
    root_element_id: str = Field(
        ..., description="The id of the root element to be used"
    )
    jwt: str = Field(..., description="The JWT token")
    project: Project = Field(..., description="The project")
    base_server: str = Field(..., description="The base server")
    websocket_server: str = Field(..., description="The websocket server")
    css_path: str = Field(..., description="The path to the CSS file")
    script_path: str = Field(..., description="The path to the script file")
    organisation_name: str = Field(default="", description="The organisation name")

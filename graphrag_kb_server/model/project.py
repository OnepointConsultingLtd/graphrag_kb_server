from enum import StrEnum
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime


class GenerationStatus(StrEnum):
    EXISTS = "exists"
    CREATED = "created"


class IndexingStatus(StrEnum):
    UNKNOWN = "unknown"
    PREPARING = "preparing"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    name: str = Field(..., description="The name of the project")
    updated_timestamp: datetime = Field(..., description="When the project was created")
    input_files: list[str] = Field(
        ..., description="The list of file names in this project"
    )
    indexing_status: IndexingStatus = Field(
        default=IndexingStatus.UNKNOWN, description="The status of the indexing"
    )

    @field_serializer("updated_timestamp")
    def serialize_updated_timestamp(self, dt: datetime, _info):
        return dt.isoformat()


class ProjectListing(BaseModel):
    projects: list[Project] = Field(..., description="The list of projects")

    def __len__(self):
        return len(self.projects)


class EngineProjectListing(BaseModel):
    graphrag_projects: ProjectListing = Field(
        ..., description="The list of GraphRAG projects"
    )
    lightrag_projects: ProjectListing = Field(
        ..., description="The list of LightRAG projects"
    )
    cag_projects: ProjectListing = Field(..., description="The list of CAG projects")

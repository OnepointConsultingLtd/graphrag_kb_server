from pydantic import BaseModel, Field, field_serializer
from datetime import datetime


class Project(BaseModel):
    name: str = Field(..., description="The name of the project")
    updated_timestamp: datetime = Field(..., description="When the tennant was created")
    input_files: list[str] = Field(
        ..., description="The list of file names in this project"
    )

    @field_serializer('updated_timestamp')
    def serialize_updated_timestamp(self, dt: datetime, _info):
        return dt.isoformat()


class ProjectListing(BaseModel):
    projects: list[Project] = Field(..., description="The list of projects")

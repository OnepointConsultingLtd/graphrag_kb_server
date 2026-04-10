from datetime import datetime
from pydantic import BaseModel, Field


class PathProperties(BaseModel):
    path: str = Field(..., description="The path of the link")
    project_id: int = Field(..., description="The project id of the path")
    last_modified: datetime = Field(..., description="The last modified date of the path")
from pydantic import BaseModel, Field


class PathLink(BaseModel):
    path: str = Field(..., description="The path of the link")
    link: str = Field(..., description="The link of the path")
    project_id: int = Field(..., description="The project id of the path")

from pydantic import BaseModel, Field

import datetime

class PathLink(BaseModel):
    path: str = Field(..., description="The path of the link")
    link: str = Field(..., description="The link of the path")
    project_id: int = Field(..., description="The project id of the path")


class LinksImageLastModified(BaseModel):
    links: list[str] = Field(..., description="The links of the path")
    image: str | None = Field(default=None, description="The path of the image")
    last_modified: datetime.datetime | None = Field(default=None, description="The last modified date of the path")
    original_path: str | None = Field(default=None, description="The original path of the path")

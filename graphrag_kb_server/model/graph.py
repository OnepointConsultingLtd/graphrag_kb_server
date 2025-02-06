from pydantic import BaseModel, Field


class CommunityReport(BaseModel):
    id: int = Field(..., description="The community identifier")
    title: str = Field(..., description="The title of the community")
    summary: str = Field(..., description="The communitty summary")
from pydantic import BaseModel, Field

class ProfileQuery(BaseModel):
    profile_id: str = Field(..., description="The ID of the profile")
    request_id: str = Field(
        default="",
        description="The request ID used to track the request",
    )
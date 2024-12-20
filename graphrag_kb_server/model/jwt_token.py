from typing import Optional

from pydantic import BaseModel, Field


class JWTToken(BaseModel):
    """JWT Token Data"""

    email: str = Field(..., description="The email")
    token: str = Field(..., description="The whole token")
    folder_name: str = Field(
        ..., description="The name of the folder with all of the GraphRAG files"
    )


class JWTTokenData(BaseModel):
    name: str = Field(..., description="The subject on the token")
    email: str = Field(..., description="The email")
    time_delta_minutes: Optional[int] = Field(
        default=None, description="Determines the expiry date of the token"
    )

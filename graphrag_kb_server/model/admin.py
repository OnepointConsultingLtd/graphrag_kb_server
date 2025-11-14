from pydantic import BaseModel, Field


class AdminUser(BaseModel):
    name: str = Field(..., description="The name of the admin user")
    email: str = Field(..., description="The email of the admin user")
    password_plain: str = Field(
        ..., description="The password plain text of the admin user"
    )
    password_hash: str | None = Field(
        default=None, description="The password hash of the admin user"
    )
    jwt_token: str = Field(default=None, description="The JWT token of the admin user")
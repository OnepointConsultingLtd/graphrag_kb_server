from pydantic import BaseModel, Field
from datetime import datetime


class Tennant(BaseModel):
    folder_name: str = Field(
        ..., description="The name of the folder in which the projects are located"
    )
    creation_timestamp: datetime = Field(
        ..., description="When the tennant was created"
    )
    token: str = Field(
        default="", description="The token of the tennant"
    )

    def as_dict(self):
        return {
            "folder_name": self.folder_name,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "token": self.token,
        }

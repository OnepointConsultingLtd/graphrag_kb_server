from pydantic import BaseModel, Field
from datetime import datetime


class Tennant(BaseModel):
    folder_name: str = Field(
        ..., description="The name of the folder in which the projects are located"
    )
    creation_timestamp: datetime = Field(
        ..., description="When the tennant was created"
    )
    token: str = Field(default="", description="The token of the tennant")
    visualization_url: str = Field(
        default="", description="The url of the visualization for this tennant"
    )
    chat_url: str = Field(
        default="", description="The url of the chat for this tennant"
    )

    def as_dict(self):
        return {
            "folder_name": self.folder_name,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "token": self.token,
            "visualization_url": self.visualization_url,
            "chat_url": self.chat_url,
        }

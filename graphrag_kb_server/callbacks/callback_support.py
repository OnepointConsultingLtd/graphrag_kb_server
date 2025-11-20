from pydantic import BaseModel


class BaseCallback(BaseModel):

    model_config = {"frozen": False}

    async def callback(self, message: str):
        pass

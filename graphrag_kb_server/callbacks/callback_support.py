from pydantic import BaseModel


class BaseCallback(BaseModel):

    model_config = {"frozen": True}

    async def callback(self, message: str):
        pass

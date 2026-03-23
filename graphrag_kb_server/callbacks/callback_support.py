from pydantic import BaseModel

from graphrag_kb_server.logger import logger


class BaseCallback(BaseModel):

    model_config = {"frozen": False}

    async def callback(self, message: str):
        pass


class InfoCallback(BaseCallback):

    async def callback(self, message: str):
        logger.info(message)

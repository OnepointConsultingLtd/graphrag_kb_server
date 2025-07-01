import json
from enum import StrEnum

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
)
from graphrag_kb_server.main import sio
from graphrag_kb_server.service.jwt_service import decode_token
from graphrag_kb_server.service.tennant import find_project_folder
from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.callbacks.callback_support import BaseCallback
from graphrag_kb_server.service.search.search_documents import retrieve_relevant_documents

class Command(StrEnum):
    START_SESSION = "start_session"
    PROGRESS = "progress"
    RESPONSE = "response"
    BUILD_CONTEXT = "build_context"
    ERROR = "error"


class WebsocketCallback(BaseCallback):

    def __init__(self, sid: str):
        self.sid = sid

    async def callback(self, message: str):
        await sio.emit(Command.PROGRESS, {"data": message}, to=self.sid)


@sio.event
async def connect(sid: str, environ):
    logger.info(f"🔥 SERVER: Client connected with SID: {sid}")
    await sio.emit(
        Command.START_SESSION,
        {"data": "Welcome to graphrag knowledge base server."},
        to=sid,
    )

@sio.event
async def start_session(sid: str, environ):
    # logger.info(f"Client connected: {sio}")
    await sio.emit(
        Command.START_SESSION,
        {"data": "Welcome to graphrag knowledge base server."},
        to=sid,
    )


@sio.event
async def relevant_documents(sid: str, token: str, project: str, document_query: str):
    try:
        logger.info(f"Document query from {sio}: {document_query}")
        token_data = await decode_token(token)
        tennant_folder = cfg.graphrag_root_dir_path / token_data["sub"]
        project_dir = find_project_folder(tennant_folder, Engine.LIGHTRAG, project)
        document_search_query = DocumentSearchQuery(**json.loads(document_query))
        callback = WebsocketCallback(sid)
        response = await retrieve_relevant_documents(project_dir, document_search_query, callback)
        await sio.emit(Command.RESPONSE, response.model_dump_json(), to=sid)
    except Exception as e:
        err_msg = f"Errors: {e}. Please try again."
        logger.error(err_msg)
        await sio.emit(Command.ERROR, {"message": err_msg}, to=sid)


@sio.event
async def disconnect(sid: str):
    logger.info(f"Client disconnected: {sio}")

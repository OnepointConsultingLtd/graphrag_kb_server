import json
import traceback
from pathlib import Path
from enum import StrEnum


from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.search.search import DocumentSearchQuery
from graphrag_kb_server.main import sio
from graphrag_kb_server.service.jwt_service import decode_token
from graphrag_kb_server.service.tennant import find_project_folder
from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.callbacks.callback_support import BaseCallback
from graphrag_kb_server.service.search.search_documents import (
    retrieve_relevant_documents,
)
from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.service.cag.cag_support import cag_get_response_stream
from graphrag_kb_server.service.graphrag.query import rag_local
from graphrag_kb_server.model.engines import find_engine


class Command(StrEnum):
    START_SESSION = "start_session"
    PROGRESS = "progress"
    RESPONSE = "response"
    BUILD_CONTEXT = "build_context"
    ERROR = "error"
    STREAM_START = "stream_start"
    STREAM_TOKEN = "stream_token"
    STREAM_END = "stream_end"


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
async def relevant_documents(
    sid: str,
    token: str,
    project: str,
    document_query: str,
    max_filepath_depth: int = 20,
):
    try:
        logger.info(f"Document query from {sio}: {document_query}")
        project_dir = await find_project_dir(token, project, Engine.LIGHTRAG)
        document_search_query = DocumentSearchQuery(
            **json.loads(document_query), max_filepath_depth=max_filepath_depth
        )
        callback = WebsocketCallback(sid)
        response = await retrieve_relevant_documents(
            project_dir, document_search_query, callback
        )
        await sio.emit(Command.RESPONSE, response.model_dump_json(), to=sid)
    except Exception as e:
        err_msg = f"Errors: {e}. Please try again."
        logger.error(err_msg)
        logger.error(f"Stack trace: {traceback.format_exc()}")
        await sio.emit(Command.ERROR, {"message": err_msg}, to=sid)


@sio.event
async def chat_stream(sid: str, token: str, project: str, query_parameters: dict):
    try:
        project_dir = await find_project_dir(
            token, project, find_engine(query_parameters["engine"])
        )
        query_parameters["context_params"]["project_dir"] = project_dir
        query_params = QueryParameters(**query_parameters)
        match query_params.engine:
            case Engine.GRAPHRAG:
                await sio.emit(Command.STREAM_START, {"data": "Stream started"}, to=sid)
                generator = await rag_local(query_params, True)
                async for event in generator:
                    await sio.emit(Command.STREAM_TOKEN, event, to=sid)
                await sio.emit(Command.STREAM_END, {"data": "Stream ended"}, to=sid)
            case Engine.LIGHTRAG:
                raise ValueError("Lightrag is not supported for chat streaming")
            case Engine.CAG:
                text_response = await cag_get_response_stream(
                    project_dir,
                    query_params.conversation_id,
                    query_params.context_params.query,
                )
                await sio.emit(Command.STREAM_START, {"data": "Stream started"}, to=sid)
                async for event in text_response:
                    await sio.emit(Command.STREAM_TOKEN, event.text, to=sid)
                await sio.emit(Command.STREAM_END, {"data": "Stream ended"}, to=sid)
            case _:
                await sio.emit(
                    Command.ERROR, {"message": "Engine not supported"}, to=sid
                )
    except Exception as e:
        err_msg = f"Errors: {e}. Please try again."
        logger.error(err_msg)
        logger.error(f"Stack trace: {traceback.format_exc()}")
        await sio.emit(Command.ERROR, {"message": err_msg}, to=sid)


@sio.event
async def disconnect(sid: str):
    logger.info(f"Client disconnected: {sio}")


async def find_project_dir(token: str, project: str, engine: Engine) -> Path:
    token_data = await decode_token(token)
    tennant_folder = cfg.graphrag_root_dir_path / token_data["sub"]
    project_dir = find_project_folder(tennant_folder, engine, project)
    return project_dir

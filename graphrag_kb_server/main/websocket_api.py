import json
import traceback
from pathlib import Path
from enum import StrEnum
from pydantic import Field


from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.search.keywords import KeywordType, Keywords
from graphrag_kb_server.model.search.search import DocumentSearchQuery
from graphrag_kb_server.main import sio
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path
from graphrag_kb_server.service.db.db_persistence_keywords import save_keywords
from graphrag_kb_server.service.jwt_service import decode_token
from graphrag_kb_server.service.lightrag.lightrag_constants import (
    KEYWORDS_SEPARATOR,
    PREFIX_HIGH_LEVEL_KEYWORDS,
    PREFIX_LOW_LEVEL_KEYWORDS,
)
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
from graphrag_kb_server.service.db.db_persistence_search import (
    insert_search_query,
    process_search_response,
    get_search_results,
)


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

    sid: str = Field(description="The SID of the websocket")
    request_id: str = Field(
        default="", description="The request ID used to track the request"
    )

    async def callback(self, message: str):
        await sio.emit(
            Command.PROGRESS,
            {"data": message, "request_id": self.request_id},
            to=self.sid,
        )


class KeywordsCallback(WebsocketCallback):

    search_history_id: int | None = None
    project_dir: Path | None = None

    async def callback(self, message: str):
        # call super to emit the message
        await super().callback(message)
        if self.search_history_id is not None and message is not None:
            is_high_level_keywords = message.startswith(PREFIX_HIGH_LEVEL_KEYWORDS)
            is_low_level_keywords = message.startswith(PREFIX_LOW_LEVEL_KEYWORDS)
            if is_high_level_keywords or is_low_level_keywords:
                keyword_type = (
                    KeywordType.HIGH_LEVEL
                    if is_high_level_keywords
                    else KeywordType.LOW_LEVEL
                )
                simple_project = extract_elements_from_path(self.project_dir)
                schema_name = simple_project.schema_name
                only_keywords = message[
                    len(
                        PREFIX_HIGH_LEVEL_KEYWORDS
                        if is_high_level_keywords
                        else PREFIX_LOW_LEVEL_KEYWORDS
                    ) :
                ].split(KEYWORDS_SEPARATOR)
                only_keywords = [keyword.strip() for keyword in only_keywords]
                try:
                    await save_keywords(
                        schema_name,
                        Keywords(
                            keywords=only_keywords,
                            keyword_type=keyword_type,
                            search_id=self.search_history_id,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error saving keywords: {e}")


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
    max_filepath_depth: int = 1000,
):
    try:
        logger.info(f"Document query from {sio}: {document_query}")
        document_search_query = DocumentSearchQuery(
            **json.loads(document_query),
            max_filepath_depth=max_filepath_depth,
            is_search_query=True,
        )
        project_dir = await find_project_dir(token, project, Engine.LIGHTRAG)
        callback = KeywordsCallback(
            sid=sid,
            request_id=document_search_query.request_id,
            project_dir=project_dir,
            search_history_id=None,
        )
        found_search_results = await get_search_results(
            project_dir, document_search_query
        )
        if found_search_results is not None:
            await callback.callback(found_search_results.response)
            await sio.emit(
                Command.RESPONSE, found_search_results.model_dump_json(), to=sid
            )
            return
        search_history_id = await insert_search_query(
            project_dir, document_search_query
        )
        callback.search_history_id = search_history_id
        logger.info(f"Document query from {sio}: {document_query}")
        await callback.callback("Searching documents...")

        response = await retrieve_relevant_documents(
            project_dir, document_search_query, callback
        )
        search_results_ids = await process_search_response(
            project_dir, search_history_id, response
        )
        await sio.emit(Command.RESPONSE, response.model_dump_json(), to=sid)
        logger.info(f"Inserted search results IDs: {search_results_ids}")
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

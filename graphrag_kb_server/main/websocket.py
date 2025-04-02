import socketio
from enum import StrEnum

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.query import rag_local
from graphrag_kb_server.model.rag_parameters import ContextParameters
from graphrag_kb_server.service.query import rag_local_build_context

sio = socketio.AsyncServer(async_mode="aiohttp")


class Command(StrEnum):
    START_SESSION = "start_session"
    RESPONSE = "response"
    BUILD_CONTEXT = "build_context"
    ERROR = "error"


@sio.event
async def connect(sid: str, environ):
    logger.info(f"Client connected: {sio}")
    await sio.emit(
        Command.START_SESSION,
        {"data": "Welcome to graphrag knowledge base server."},
        to=sid,
    )


@sio.event
async def query_websocket(sid: str, question: str):
    logger.info(f"Query from {sio}: {question}")
    response = await rag_local(
        ContextParameters(
            query=question,
            project_dir=cfg.graphrag_root_dir_path,
            context_size=cfg.local_context_max_tokens,
        )
    )
    await sio.emit(Command.RESPONSE, {"data": response}, to=sid)


@sio.event
async def build_context(sid: str, question: str):
    logger.info(f"Building context for {sio}: {question}")
    context_text, context_records = rag_local_build_context(
        ContextParameters(
            query=question,
            project_dir=cfg.graphrag_root_dir_path,
            context_size=cfg.local_context_max_tokens,
        )
    )
    await sio.emit(
        Command.BUILD_CONTEXT,
        {
            "data": {
                "context_text": context_text,
                "context_records": context_records,
            }
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sio}")

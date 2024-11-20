import asyncio
import socketio

from aiohttp import web
from enum import StrEnum
from typing import Awaitable

from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg
from graphrag_kb_server.config import websocket_cfg
from graphrag_kb_server.service.query import rag_local, rag_global
from graphrag_kb_server.service.query import rag_local_build_context, rag_global_build_context

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings

sio = socketio.AsyncServer(async_mode="aiohttp")
routes = web.RouteTableDef()

class Command(StrEnum):
    START_SESSION = "start_session"
    RESPONSE = "response"
    BUILD_CONTEXT = "build_context"
    ERROR = "error"


class Format(StrEnum):
    HTML = "html"
    JSON = "json"


class Search(StrEnum):
    LOCAL = "local"
    GLOBAL = "global"


@sio.event
async def connect(sid: str, environ):
    logger.info(f"Client connected: {sio}")
    await sio.emit(
        Command.START_SESSION,
        {"data": "Welcome to graphrag knowledge base server."},
        to=sid,
    )


@sio.event
async def query(sid: str, question: str):
    logger.info(f"Query from {sio}: {question}")
    response = await rag_local(question, cfg.graphrag_root_dir_path)
    await sio.emit(Command.RESPONSE, {"data": response}, to=sid)


@sio.event
async def build_context(sid: str, question: str):
    logger.info(f"Building context for {sio}: {question}")
    context_text, context_records = rag_local_build_context(
        question, cfg.graphrag_root_dir_path
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


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    return web.json_response({"status": "OK"})


HTML_CONTENT = (
    "<html><body><h1>{question}</h1><section>{response}</section></body></html>"
)


async def handle_error(fun: Awaitable, **kwargs) -> any:
    try:
        request = kwargs["request"]
        return await fun(request)
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        return web.Response(
            text=f"<html><body>{e}</body></html>", content_type="text/html"
        )


@routes.get("/about")
async def about(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the information about the current knowledge base
    tags:
      - context
    responses:
      '200':
        description: Expected response to a valid request
    """
    async def handle_request(request: web.Request):
        question = "What are the main topics?"
        response = await rag_local(question, cfg.graphrag_root_dir_path)
        return web.Response(
            text=HTML_CONTENT.format(question=question, response=response),
            content_type="text/html",
        )

    return await handle_error(handle_request, request=request)


DEFAULT_QUESTION = "What are the main topics?"


@routes.get("/query")
async def query(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the response to a query from an LLM
    tags:
      - context
    parameters:
      - name: question
        in: query
        required: true
        description: The question for which the context is retrieved. For example\: What are the main topics?
        schema:
          type: string
      - name: format
        in: query
        required: false
        description: The format of the output (json, html)
        schema:
          type: string
          enum: [json, html]  # Enumeration for the dropdown
      - name: search
        in: query
        required: false
        description: The type of the search (local, global)
        schema:
          type: string
          enum: [local, global]  # Enumeration for the dropdown
    responses:
      '200':
        description: Expected response to a valid request
    """
    async def handle_request(request: web.Request):
        question = request.rel_url.query.get("question", DEFAULT_QUESTION)
        format = request.rel_url.query.get("format", Format.JSON.value)
        search = request.rel_url.query.get("search", Search.LOCAL.value)
        match search:
            case Search.GLOBAL:
                response = await rag_global(question, cfg.graphrag_root_dir_path)
            case _:
                response = await rag_local(question, cfg.graphrag_root_dir_path)
        match format:
            case Format.HTML:
                return web.Response(
                    text=HTML_CONTENT.format(question=question, response=response),
                    content_type="text/html",
                )
            case _:
                return web.json_response({"question": question, "response": response})
        raise web.HTTPBadRequest(text="Please make sure the format is specified.")

    return await handle_error(handle_request, request=request)


@routes.get("/context")
async def context(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the context used by on a specific request
    tags:
      - context
    parameters:
      - name: question
        in: query
        required: true
        description: The question for which the context is retrieved. For example\: What are the main topics?
        schema:
          type: string
      - name: use_context_records
        in: query
        required: false
        description: The format of the output
        schema:
          type: boolean
      - name: search
        in: query
        required: false
        description: The type of the search (local, global)
        schema:
          type: string
          enum: [local, global]  # Enumeration for the dropdown
    responses:
      '200':
        description: Expected response to a valid request
    """
    async def handle_request(request: web.Request):
        question = request.rel_url.query.get("question", DEFAULT_QUESTION)
        search = request.rel_url.query.get("search", Search.LOCAL.value)
        use_context_records = (
            request.rel_url.query.get("use_context_records", "false") == "true"
        )

        match search:
            case Search.GLOBAL:
                context_text, context_records = rag_global_build_context(
                    question, cfg.graphrag_root_dir_path
                )
            case _:
                context_text, context_records = rag_local_build_context(
                    question, cfg.graphrag_root_dir_path
                )
        return web.json_response(
            {
                "context_text": context_text,
                "context_records": (
                    {kv[0]: kv[1].to_dict() for kv in context_records.items()}
                    if use_context_records
                    else None
                ),
            }
        )

    return await handle_error(handle_request, request=request)


def run_server():

    app = web.Application()
    sio.attach(app)

    loop = asyncio.new_event_loop()

    # Define Swagger schema
    swagger_info = SwaggerInfo(
        title="Graph RAG Knowledge Base Server",
        version="1.0.0",
        description="APIs for RAG based on a pre-determined knowledge base",
    )
    swagger = SwaggerDocs(app, info=swagger_info, swagger_ui_settings=SwaggerUiSettings(path="/docs/"))
    swagger.add_routes(routes)

    app.add_routes(routes)

    web.run_app(
        app,
        host=websocket_cfg.websocket_server,
        port=websocket_cfg.websocket_port,
        loop=loop,
    )


if __name__ == "__main__":
    logger.info("Starting server ...")
    run_server()
    logger.info("Graph RAG Knowledge Base Server stopped.")

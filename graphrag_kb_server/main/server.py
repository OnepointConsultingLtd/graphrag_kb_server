import asyncio
import socketio

from aiohttp import web
from enum import StrEnum
from typing import Awaitable

from yarl import URL

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings

from graphrag_kb_server.model.rag_parameters import ContextParameters

from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg
from graphrag_kb_server.config import websocket_cfg
from graphrag_kb_server.service.query import rag_local, rag_global
from graphrag_kb_server.service.query import (
    rag_local_build_context,
    rag_global_build_context,
    rag_combined_context,
)

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
    ALL = "all"


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
        response = await rag_local(
            ContextParameters(
                query=question,
                project_dir=cfg.graphrag_root_dir_path,
                context_size=cfg.local_context_max_tokens,
            )
        )
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
        description: The question for which the context is retrieved. For example 'What are the main topics?'
        schema:
          type: string
      - name: format
        in: query
        required: false
        description: The format of the output (json, html)
        schema:
          type: string
          enum: [json, html]
      - name: search
        in: query
        required: false
        description: The type of the search (local, global)
        schema:
          type: string
          enum: [local, global]
      - name: context_size
        in: query
        required: false
        description: The size of the context, like eg 14000
        schema:
          type: integer
          format: int32
    responses:
      '200':
        description: Expected response to a valid request
    """

    async def handle_request(request: web.Request):
        format = request.rel_url.query.get("format", Format.JSON.value)
        search = request.rel_url.query.get("search", Search.LOCAL.value)
        context_params = create_context_parameters(request.rel_url)
        match search:
            case Search.GLOBAL:
                response = await rag_global(context_params)
            case _:
                response = await rag_local(context_params)
        match format:
            case Format.HTML:
                return web.Response(
                    text=HTML_CONTENT.format(
                        question=context_params.query, response=response
                    ),
                    content_type="text/html",
                )
            case _:
                return web.json_response(
                    {"question": context_params.query, "response": response}
                )
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
        description: The question for which the context is retrieved. For example 'What are the main topics?'
        schema:
          type: string
      - name: use_context_records
        in: query
        required: false
        description: Whether to output the context records or not.
        schema:
          type: boolean
      - name: search
        in: query
        required: false
        description: The type of the search (local, global)
        schema:
          type: string
          enum: [local, global, all]  # Enumeration for the dropdown
      - name: context_size
        in: query
        required: false
        description: The size of the context, like eg 14000
        schema:
          type: integer
          format: int32
    responses:
      '200':
        description: Expected response to a valid request
    """

    async def handle_request(request: web.Request):
        search = request.rel_url.query.get("search", Search.LOCAL.value)
        use_context_records = (
            request.rel_url.query.get("use_context_records", "false") == "true"
        )
        context_params = create_context_parameters(request.rel_url)

        def process_records(records):
            return (
                {kv[0]: kv[1].to_dict() for kv in records.items()}
                if use_context_records
                else None
            )

        match search:
            case Search.GLOBAL:
                context_text, context_records = rag_global_build_context(context_params)
                context_records = process_records(context_records)
            case Search.ALL:
                context_text, context_records = rag_combined_context(context_params)
                context_records = {
                    "local": process_records(context_records["local"]),
                    "global": process_records(context_records["global"]),
                }
            case _:
                context_text, context_records = rag_local_build_context(context_params)
                context_records = process_records(context_records)
        logger.info(f"Sending context with length: {len(context_text)}.")
        return web.json_response(
            {
                "context_text": context_text,
                "context_records": context_records,
            }
        )
    
    return await handle_error(handle_request, request=request)


def create_context_parameters(url: URL) -> ContextParameters:
    question = url.query.get("question", DEFAULT_QUESTION)
    context_size = url.query.get("context_size", cfg.local_context_max_tokens)
    return ContextParameters(
        query=question,
        project_dir=cfg.graphrag_root_dir_path,
        context_size=context_size,
    )


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
    swagger = SwaggerDocs(
        app, info=swagger_info, swagger_ui_settings=SwaggerUiSettings(path="/docs/")
    )
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

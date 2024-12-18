import asyncio
import socketio
import base64
import zipfile
from typing import Tuple, Dict, Optional

from aiohttp import web
from enum import StrEnum
from typing import Awaitable

from yarl import URL

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings

from graphrag_kb_server.model.rag_parameters import ContextParameters
from graphrag_kb_server.model.context import Search

from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg
from graphrag_kb_server.config import websocket_cfg
from graphrag_kb_server.service.query import rag_local, rag_global, rag_drift
from graphrag_kb_server.service.query import (
    rag_local_build_context,
    rag_global_build_context,
    rag_combined_context,
    rag_drift_context
)
from graphrag_kb_server.service.index import clear_rag, acreate_graph_rag

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
        if "response_format" in kwargs:
            match kwargs["response_format"]:
                case Format.JSON:
                    return web.json_response({"error": e}, status=400)
        return web.json_response(
            {"message": str(e)},
            status=500,
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


@routes.post("/upload_index")
async def upload_index(request: web.Request) -> web.Response:
    """
    File Upload and Index
    ---
    summary: Uploads a files with a knowledge base
    tags:
      - index
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              file:
                type: string
                format: binary
                description: The zip file to be uploaded.
              upload_secret:
                type: string
    responses:
      "200":
        description: Successful upload
        content:
          application/json:
            example:
              status: "success"
              message: "1 file uploaded and extracted to /path/to/upload/dir."
      "400":
        description: Bad Request - No file uploaded or invalid file format.
        content:
          application/json:
            example:
              status: "error"
              message: "No file was uploaded"
    """

    async def handle_request(request: web.Request) -> web.Response:
        saved_files = []
        body = request["data"]["body"]
        file = body["file"]
        file_name = body["file_name"]
        upload_secret = body["upload_secret"]
        if upload_secret != cfg.upload_secret:
            return web.json_response({"error": "The secret is not right."}, status=401)
        # Save zip file
        if file_name is not None and file_name.lower().endswith(".zip"):
            with open(uploaded_file := cfg.upload_dir / file_name, "wb") as f:
                f.write(base64.b64decode(file))
                saved_files.append(uploaded_file)
        if (file_length := len(saved_files)) == 0:
            return web.json_response({"error": "No file was uploaded"}, status=400)
        # Extract the zip file
        upload_folder = cfg.upload_dir / saved_files[0].stem
        try:
            with zipfile.ZipFile(saved_files[0], "r") as zip_ref:
                zip_ref.extractall(upload_folder)
        except zipfile.BadZipFile:
            return web.json_response(
                {"error": "Uploaded file is not a valid zip file"}, status=400
            )
        clear_rag()
        await acreate_graph_rag(True, upload_folder)
        return web.json_response(
            {
                "message": f"{file_length} file{"" if len(saved_files) == 0 else ""} uploaded, extracted and indexed from {cfg.upload_dir}."
            },
            status=200,
        )

    return await handle_error(
        handle_request, request=request, response_format=Format.JSON.value
    )


@routes.get("/query")
async def query(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the response to a query from an LLM
    tags:
      - query
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
        description: The type of the search (local, global, drift)
        schema:
          type: string
          enum: [local, global, drift]
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
            case Search.DRIFT:
                response = await rag_drift(context_params)
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
          enum: [local, global, drift, all]  # Enumeration for the dropdown
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

        def process_records(records: Optional[dict]):
            if not records:
                return {}
            return (
                {kv[0]: kv[1].to_dict() for kv in records.items()}
                if use_context_records
                else None
            )

        match search:
            case Search.GLOBAL:
                context_builder_result = await rag_global_build_context(context_params)
            case Search.ALL:
                context_builder_result = await rag_combined_context(context_params)
            case Search.DRIFT:
                context_builder_result = await rag_drift_context(context_params)
            case _:
                context_builder_result = rag_local_build_context(context_params)
        return web.json_response(
            {
                "context_text": context_builder_result.context_text,
                "local_context_records": process_records(
                    context_builder_result.local_context_records
                ),
                "global_context_records": process_records(
                    context_builder_result.global_context_records
                ),
            }
        )

    return await handle_error(handle_request, request=request)


@routes.delete("/delete_index")
async def delete_index(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the response to a query from an LLM
    tags:
      - delete
    responses:
      '200':
        description: Expected response to a valid request
    """

    async def handle_request(request: web.Request):
        deleted = clear_rag()
        return web.json_response(
            {
                "deleted": deleted,
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


async def multipart_form(request: web.Request) -> Tuple[Dict, bool]:
    reader = await request.multipart()
    d = {}
    while True:
        field = await reader.next()
        if field is None:
            break
        field_name = field.name
        if field_name == "file":
            d[field_name] = base64.b64encode(await field.read())
            d[f"{field_name}_name"] = field.filename
        else:
            d[field_name] = (await field.read()).decode("utf-8")
    return d, True


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
    swagger.register_media_type_handler(
        media_type="multipart/form-data", handler=multipart_form
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

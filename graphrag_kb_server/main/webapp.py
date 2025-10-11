from typing import Tuple, Dict
from pathlib import Path

import asyncio
import base64
from urllib.parse import urlparse

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings
from aiohttp import web

from graphrag_kb_server.config import cfg, websocket_cfg
from graphrag_kb_server.main import all_routes, sio

from graphrag_kb_server.main.multi_tennant_server import auth_middleware
from graphrag_kb_server.logger import logger, init_logger
from graphrag_kb_server.service.jwt_service import (
    generate_admin_token,
    save_security_yaml,
)
from graphrag_kb_server.service.snippet_generation_service import find_chat_assets
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.websocket_api import *


init_logger()

FILE_INDEX = "index.html"
GRAPHRAG_INDEX = (Path(__file__) / f"../../../front_end/dist/{FILE_INDEX}").resolve()
GRAPHRAG_LINKS = ["/graphrag.htm", "/graphrag.html", "/graphrag"]
CHAT_INDEX = (Path(__file__) / f"../../../front_end_chat/dist/{FILE_INDEX}").resolve()
CHAT_LINKS = [
    "/chat",
    "/dashboard",
    "/login",
    "/floating-chat",
    "/admin",
    "/administrator",
]

for link in [GRAPHRAG_INDEX, CHAT_INDEX]:
    assert (
        link.exists()
    ), f"Cannot find the path of the user interface ({link}). Please build it first with 'yarn run build' in the front_end directory."


logger.info(f"PATH_INDEX: {GRAPHRAG_INDEX}")


@web.middleware
async def static_routing_middleware(request: web.Request, handler):

    if request.method == "OPTIONS":
        return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)

    if request.method == "GET":
        path = request.path

        # Skip routing for API endpoints and specific routes
        if (
            path.startswith("/protected/")
            or path.startswith("/tennant/")
            or path in GRAPHRAG_LINKS
            or path in CHAT_LINKS
        ):
            return await handler(request)

        # Route static files based on referer
        file_path = None
        referer = request.headers.get("Referer", "")
        address = urlparse(referer).path
        if any(address.endswith(link) for link in GRAPHRAG_LINKS):
            file_path = GRAPHRAG_INDEX.parent / path.lstrip("/")
        elif any(address.endswith(link) for link in CHAT_LINKS):
            file_path = CHAT_INDEX.parent / path.lstrip("/")

        if file_path and file_path.exists() and file_path.is_file():
            return web.FileResponse(path=file_path, headers=CORS_HEADERS)

        # Just the necessary stuff for the chat UI
        _, css_files, script_files = find_chat_assets()
        for css_file in css_files:
            if path.endswith(css_file.name):
                return web.FileResponse(path=css_file, headers=CORS_HEADERS)
        for script_file in script_files:
            if path.endswith(script_file.name):
                return web.FileResponse(path=script_file, headers=CORS_HEADERS)

    return await handler(request)


async def get_visualization_graphrag(_: web.Request) -> web.Response:
    return web.FileResponse(GRAPHRAG_INDEX)


async def get_chat_ui(_: web.Request) -> web.Response:
    return web.FileResponse(CHAT_INDEX)


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

    app = web.Application(middlewares=[static_routing_middleware, auth_middleware])
    app.middlewares.append(auth_middleware)
    logger.info("Set up application ...")
    sio.attach(app)

    loop = asyncio.new_event_loop()
    logger.info("Event loop created ...")

    # Define Swagger schema
    swagger_info = SwaggerInfo(
        title="Graph RAG Knowledge Base Server",
        version="1.0.0",
        description="APIs for RAG based on a pre-determined knowledge base",
    )
    swagger = SwaggerDocs(
        app,
        info=swagger_info,
        swagger_ui_settings=SwaggerUiSettings(path="/docs/"),
        security=cfg.config_dir / "security.yaml",
    )
    swagger.register_media_type_handler(
        media_type="multipart/form-data", handler=multipart_form
    )
    logger.info("Swagger registered ...")
    for routes in all_routes:
        swagger.add_routes(routes)
    logger.info("Routes added ...")
    for url in GRAPHRAG_LINKS:
        app.router.add_get(url, get_visualization_graphrag)
    for url in CHAT_LINKS:
        app.router.add_get(url, get_chat_ui)

    # app.router.add_static('/', GRAPHRAG_INDEX.parent)

    logger.info("Static files added ...")
    web.run_app(
        app,
        host=websocket_cfg.websocket_server,
        port=websocket_cfg.websocket_port,
        loop=loop,
    )


if __name__ == "__main__":
    logger.info("Starting server ...")
    generate_admin_token()
    save_security_yaml()
    run_server()
    logger.info("Graph RAG Knowledge Base Server stopped.")

from typing import Tuple, Dict
from pathlib import Path
import asyncio
import base64

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings
from aiohttp import web

from graphrag_kb_server.config import cfg, websocket_cfg
from graphrag_kb_server.main import all_routes

from graphrag_kb_server.main.multi_tennant_server import auth_middleware
from graphrag_kb_server.logger import logger, init_logger
from graphrag_kb_server.service.jwt_service import (
    generate_admin_token,
    save_security_yaml,
)

init_logger()

# from graphrag_kb_server.main.websocket import sio

FILE_INDEX = "index.html"
PATH_INDEX = (Path(__file__) / f"../../../front_end/dist/{FILE_INDEX}").resolve()
INDEX_LINKS = ["/graphrag.htm", "/graphrag.html", "/graphrag"]

assert (
    PATH_INDEX.exists()
), f"Cannot find the path of the user interface ({PATH_INDEX}). Please build it first with 'yarn run build' in the front_end directory."

logger.info(f"PATH_INDEX: {PATH_INDEX}")


async def get_visualization_graphrag(_: web.Request) -> web.Response:
    return web.FileResponse(PATH_INDEX)


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
    app.middlewares.append(auth_middleware)
    logger.info("Set up application ...")
    # sio.attach(app)

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
    for url in INDEX_LINKS:
        app.router.add_get(url, get_visualization_graphrag)
    app.router.add_static("/", path=PATH_INDEX.parent, name="root")
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

from typing import Tuple, Dict
import asyncio
import base64

from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo, SwaggerUiSettings
from aiohttp import web

from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg, websocket_cfg
from graphrag_kb_server.main import all_routes, auth_middleware
from graphrag_kb_server.main.server import sio


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
    sio.attach(app)

    loop = asyncio.new_event_loop()

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
    for routes in all_routes:
        swagger.add_routes(routes)

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

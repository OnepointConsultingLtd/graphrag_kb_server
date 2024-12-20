from typing import Awaitable
from aiohttp import web

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.web_format import Format

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
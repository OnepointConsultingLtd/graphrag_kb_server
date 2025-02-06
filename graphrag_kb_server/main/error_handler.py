from typing import Awaitable
from aiohttp import web
from aiohttp.web import Response

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.main.cors import CORS_HEADERS

async def handle_error(fun: Awaitable, **kwargs) -> any:
    try:
        request = kwargs["request"]
        return await fun(request)
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        if "response_format" in kwargs:
            match kwargs["response_format"]:
                case Format.JSON:
                    return web.json_response({"error": str(e)}, status=400)
        return web.json_response(
            {"message": str(e)},
            status=500,
        )


def invalid_response(
    error_name: str,
    error_description: str,
    error_code: ErrorCode = ErrorCode.INVALID_INPUT,
    status: int = 400
) -> Response:
    return web.json_response(
        Error(
            error_code=error_code,
            error=error_name,
            description=error_description,
        ).model_dump(),
        status=status,
        headers=CORS_HEADERS
    )

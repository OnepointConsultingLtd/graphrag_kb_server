from aiohttp import web
from markdown import markdown

from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.context import Search
from graphrag_kb_server.service.query import rag_local, rag_global, rag_drift
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.simple_template import HTML_CONTENT
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.service.graphrag.prompt_factory import (
    inject_system_prompt_to_query_params,
)
from graphrag_kb_server.service.cag.cag_support import cag_get_response


async def execute_query(query_params: QueryParameters) -> web.Response:
    format, search, engine, context_params = (
        query_params.format,
        query_params.search,
        query_params.engine,
        query_params.context_params,
    )
    match engine:
        case Engine.GRAPHRAG:
            context_params = inject_system_prompt_to_query_params(query_params)
            match search:
                case Search.GLOBAL:
                    response = await rag_global(query_params)
                case Search.DRIFT:
                    response = await rag_drift(context_params)
                case _:
                    response = await rag_local(query_params)
            chat_response = ChatResponse(
                question=context_params.query,
                response=response,
            )
        case Engine.LIGHTRAG:
            match search:
                case Search.GLOBAL | Search.LOCAL | Search.ALL | Search.NAIVE:
                    if search == Search.ALL:
                        query_params.search = "hybrid"
                    chat_response = await lightrag_search(query_params)
                case _:
                    raise web.HTTPBadRequest(
                        text="LightRAG does not support local search",
                        headers=CORS_HEADERS,
                    )
        case Engine.CAG:
            text_response = await cag_get_response(
                query_params.context_params.project_dir,
                query_params.conversation_id,
                query_params.context_params.query,
            )
            chat_response = ChatResponse(
                question=context_params.query,
                response=text_response,
            )
    match format:
        case Format.HTML:
            return web.Response(
                text=HTML_CONTENT.format(
                    question=context_params.query,
                    response=markdown(chat_response.response),
                ),
                content_type="text/html",
                headers=CORS_HEADERS,
            )
        case Format.MARKDOWN:
            return web.Response(
                text=chat_response.response,
                content_type="text/plain",
                headers=CORS_HEADERS,
            )
        case Format.JSON:
            return web.json_response(
                chat_response.model_dump(),
                headers=CORS_HEADERS,
            )
    raise web.HTTPBadRequest(text="Please make sure the format is specified.")

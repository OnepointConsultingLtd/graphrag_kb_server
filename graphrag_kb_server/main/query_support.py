import re
from pathlib import Path
from aiohttp import web
from markdown import markdown

from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.context import Search
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path, get_project_id, get_project_id_from_path
from graphrag_kb_server.service.db.db_persistence_links import get_links_by_path
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.simple_template import HTML_CONTENT
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.service.cag.cag_support import cag_get_response


async def execute_query(query_params: QueryParameters) -> web.Response:
    format, search, engine, context_params = (
        query_params.format,
        query_params.search,
        query_params.engine,
        query_params.context_params,
    )
    match engine:
        case Engine.LIGHTRAG:
            match search:
                case Search.GLOBAL | Search.LOCAL | Search.ALL | Search.NAIVE:
                    if search == Search.ALL:
                        query_params = query_params.model_copy(
                            update={"search": "hybrid"}
                        )
                    chat_response = await lightrag_search(query_params)
                    chat_response = await add_links_to_response(chat_response, query_params.context_params.project_dir)
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


async def add_links_to_response(chat_response: ChatResponse, project_dir: Path):
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id(
        schema_name, simple_project.project_name, simple_project.engine.value
    )
    if chat_response.response is None:
        return
    if isinstance(chat_response.response, dict):
        enhanced_references = []
        references = chat_response.response["references"]
        for reference in references:
            file = reference["file"]
            file_path = Path(file)
            if file_path.exists():
                file_path_str = re.sub(r"^[^/]*/", "/", file_path.as_posix())
                links = await get_links_by_path(schema_name, project_id, file_path_str)
                reference["links"] = links
                enhanced_references.append(reference)
        chat_response.response["references"] = enhanced_references
    return chat_response

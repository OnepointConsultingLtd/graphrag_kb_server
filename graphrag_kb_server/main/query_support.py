import datetime
import re
import json
from pathlib import Path
from aiohttp import web
from markdown import markdown

from graphrag_kb_server.model.path_link import LinksImageLastModified
from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.context import Search
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id,
)
from graphrag_kb_server.service.db.db_persistence_links import get_links_by_path
from graphrag_kb_server.service.db.db_persistence_path_properties import get_lastmodified_by_path
from graphrag_kb_server.service.file_find_service import find_original_file
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.simple_template import HTML_CONTENT
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.service.cag.cag_support import cag_get_response
from graphrag_kb_server.logger import logger


async def execute_query(query_params: QueryParameters) -> web.Response:
    fmt, search, engine, context_params = (
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
                    chat_response = await add_links_to_response(
                        chat_response, query_params.context_params.project_dir
                    )
                case _:
                    raise web.HTTPBadRequest(
                        text=f"Unsupported search type for LightRAG: {search}", headers=CORS_HEADERS
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
        case _:
            raise web.HTTPBadRequest(
                text=f"Unsupported engine: {engine}", headers=CORS_HEADERS
            )
    match fmt:
        case Format.HTML:
            response_text = chat_response.response
            if isinstance(response_text, dict):
                response_text = json.dumps(response_text)
            return web.Response(
                text=HTML_CONTENT.format(
                    question=context_params.query,
                    response=markdown(response_text),
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


async def add_links_to_response(chat_response: ChatResponse, project_dir: Path) -> ChatResponse:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id(
        schema_name, simple_project.project_name, simple_project.engine.value
    )
    if chat_response.response is None:
        return chat_response
    if isinstance(chat_response.response, dict):
        if chat_response.response.get("references"):
            # If the reference is type KG remove it from the response.
            chat_response.response["references"] = [
                ref for ref in chat_response.response["references"]
                if ref["type"] != "KG"
            ]
            # Dedupe the references based on the "file" field.
            chat_response.response["references"] = list({r["file"]: r for r in chat_response.response["references"]}.values())
            for reference in chat_response.response["references"]:
                file_path = Path(reference["file"])
                links_image_last_modified = await get_links_and_image_by_path(file_path, schema_name, project_id, project_dir)
                links, image_path, last_modified, original_path = (
                    links_image_last_modified.links, 
                    links_image_last_modified.image, 
                    links_image_last_modified.last_modified, 
                    links_image_last_modified.original_path
                )
                reference["links"] = links
                if image_path is not None:
                    reference["image"] = image_path
                if last_modified is not None:
                    reference["last_modified"] = last_modified.isoformat()
                if original_path is not None:
                    reference["original_path"] = original_path
        elif chat_response.response.get("documents"):
            for document in chat_response.response["documents"]:
                file_path = Path(document["document_path"])
                links_image_last_modified = await get_links_and_image_by_path(file_path, schema_name, project_id, project_dir)
                links, image_path, last_modified, original_path = (
                    links_image_last_modified.links,
                    links_image_last_modified.image,
                    links_image_last_modified.last_modified,
                    links_image_last_modified.original_path
                )
                document["links"] = links
                if image_path is not None:
                    document["image"] = image_path
                if last_modified is not None:
                    document["last_modified"] = last_modified.isoformat()
                if original_path is not None:
                    document["original_path"] = original_path
        
    return chat_response


async def enrich_text_units_context(text_units_context: list[dict], project_dir: Path) -> None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id(
        schema_name, simple_project.project_name, simple_project.engine.value
    )
    for text_unit in text_units_context:
        file = text_unit.get("file_path")
        if file is not None:    
            file_path = Path(file)
            links_image_last_modified = await get_links_and_image_by_path(file_path, schema_name, project_id, project_dir)
            links, image_path, last_modified, _original_path = (
                links_image_last_modified.links,
                links_image_last_modified.image,
                links_image_last_modified.last_modified,
                links_image_last_modified.original_path
            )
            text_unit["links"] = links
            if image_path is not None:
                text_unit["image"] = image_path
            if last_modified is not None:
                text_unit["last_modified"] = last_modified.isoformat()



async def get_links_and_image_by_path(
    file_path: Path, 
    schema_name: str, 
    project_id: int, 
    project_dir: Path
) -> LinksImageLastModified:
    # Convert path first (strips Windows drive prefix e.g. C:/ → /) so it
    # resolves correctly on Linux even when the index was built on Windows.
    file_path_str = _convert_path_to_text(file_path)
    file_path = Path(file_path_str)

    # DB lookups have no filesystem dependency — always run them.
    links = await get_links_by_path(schema_name, project_id, file_path_str)
    last_modified = await get_lastmodified_by_path(schema_name, file_path_str, project_id)

    # Image lookup requires the file to exist on disk.
    if not file_path.exists():
        return LinksImageLastModified(
            links=links, 
            image=None, 
            last_modified=last_modified, 
            original_path=None
        )

    original_input = project_dir / "original_input"
    input_dir = project_dir / "input"

    def _doc_exists(file_path: Path) -> tuple[bool, Path]:
        if not file_path.exists():
            file_path = file_path.parent / file_path.name.replace("_", " ")
            exists = file_path.exists()
        else:
            exists = True
        return exists, file_path

    try:
        # Extract from file_path the path after input
        relative_path = file_path.relative_to(input_dir).as_posix()
        original_file_path = original_input / relative_path
        # Now change the txt to pdf and verify if the pdf exists
        pdf_path = original_file_path.with_suffix(".pdf")
        docx_path = original_file_path.with_suffix(".docx")
        pptx_path = original_file_path.with_suffix(".pptx")
        pdf_exists, pdf_path = _doc_exists(pdf_path)
        docx_exists, docx_path = _doc_exists(docx_path)
        pptx_exists, pptx_path = _doc_exists(pptx_path)
        if not pdf_exists and not docx_exists and not pptx_exists:
            return LinksImageLastModified(
                links=links, 
                image=None, 
                last_modified=last_modified, 
                original_path=None
            )
        # Now get the image
        if pdf_exists:
            original_path = pdf_path
            image_path = pdf_path.with_suffix(".png")
        elif docx_exists:
            original_path = docx_path
            image_path = docx_path.with_suffix(".png")
        elif pptx_exists:
            original_path = pptx_path
            image_path = pptx_path.with_suffix(".png")
        else:
            original_path = pdf_path
            image_path = pdf_path.with_suffix(".png")
        if image_path.exists():
            image_path = image_path.relative_to(project_dir)
            return LinksImageLastModified(
                links=links, 
                image=image_path.as_posix(), 
                last_modified=last_modified, 
                original_path=original_path.as_posix()
            )
        else:
            return LinksImageLastModified(
                links=links, 
                image=None, 
                last_modified=last_modified, 
                original_path=original_path.as_posix()
            )
    except Exception as e:
        logger.error(f"Error getting image by path: {e}")
        return LinksImageLastModified(
            links=links, 
            image=None, 
            last_modified=last_modified, 
            original_path=None
        )


def _convert_path_to_text(file_path: Path) -> str:
    return re.sub(r"^[^/]*/", "/", file_path.as_posix())
import zipfile
import io
import re
from pathlib import Path
from typing import Optional, Callable, Awaitable

from aiohttp import web

from yarl import URL
from markdown import markdown
from aiohttp.web import Response

from graphrag_kb_server.model.rag_parameters import ContextParameters
from graphrag_kb_server.model.context import Search

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.service.query import rag_local, rag_global, rag_drift
from graphrag_kb_server.service.query import (
    rag_local_build_context,
    rag_global_build_context,
    rag_combined_context,
    rag_drift_context,
)
from graphrag_kb_server.service.project import (
    clear_rag,
    acreate_graph_rag,
    list_projects as project_listing,
)
from graphrag_kb_server.service.zip_service import zip_input
from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.service.index_support import unzip_file
from graphrag_kb_server.service.community_service import (
    prepare_community_extraction,
    generate_gexf_file,
    find_community,
    generate_entities_digraph_gexf_file,
)
from graphrag_kb_server.utils.file_support import write_uploaded_file
from graphrag_kb_server.model.engines import find_engine_from_query, find_engine, Engine
from graphrag_kb_server.service.tennant import find_project_folder
from graphrag_kb_server.service.lightrag.lightrag_index_support import acreate_lightrag
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search

routes = web.RouteTableDef()

HTML_CONTENT = "<html><body style='font-family: sans-serif'><h1>{question}</h1><section>{response}</section></body></html>"


def extract_tennant_folder(request: web.Request) -> Path | Response:
    token_data = request["token_data"]
    if token_data is None:
        return invalid_response(
            "No tennant information", "No tennant information available in request"
        )
    tennant_folder = cfg.graphrag_root_dir_path / token_data["sub"]
    if not tennant_folder.exists():
        return invalid_response("No tennant folder", "Tennant folder was deleted.")
    return tennant_folder


def handle_project_folder(
    request: web.Request, tennant_folder: Path
) -> Path | Response:
    engine = find_engine_from_query(request)
    project = request.rel_url.query.get("project", Format.JSON.value)
    project_dir: Path = find_project_folder(tennant_folder, engine, project)
    if not project_dir.exists():
        return invalid_response(
            "No project folder found",
            f"There is no project folder {project}",
        )
    return project_dir


def match_process_dir(request: web.Request) -> Response | Path:
    match extract_tennant_folder(request):
        case Response() as error_response:
            return error_response
        case Path() as tennant_folder:
            match handle_project_folder(request, tennant_folder):
                case Response() as error_response:
                    return error_response
                case Path() as project_dir:
                    return project_dir


async def process_community_query(
    request: web.Request,
    process_community: Callable[[Path, str], Awaitable[web.Response]],
) -> Response:
    match match_process_dir(request):
        case Response() as error_response:
            return error_response
        case Path() as project_dir:
            community_id = request.match_info.get("id", None)
            if community_id is None:
                return invalid_response(
                    "No community id", "Please specify the community id."
                )
            return await process_community(project_dir, community_id)


def send_gexf_file(project_dir: Path, graph_file: Path) -> Path:
    return web.FileResponse(
        graph_file,
        headers={
            "CONTENT-DISPOSITION": f'attachment; filename="{project_dir.name}.gexf"',
            **CORS_HEADERS,
        },
    )


def get_search(request: web.Request) -> str:
    return request.rel_url.query.get("search", Search.LOCAL.value)


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    return web.json_response({"status": "OK"})


@routes.get("/protected/project/about")
async def about(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the information about the current knowledge base of a specific project.
    tags:
      - project
    security:
      - bearerAuth: []
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: search
        in: query
        required: false
        description: The type of the search (local, global)
        schema:
          type: string
          enum: [local, global]
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag]
    responses:
      '200':
        description: Expected response to a valid request
      '400':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              status: "error"
              message: "No file was uploaded"
    """

    async def handle_request(request: web.Request) -> web.Response:
        match extract_tennant_folder(request):
            case Response() as error_response:
                return error_response
            case Path() as tennant_folder:
                match handle_project_folder(request, tennant_folder):
                    case Response() as error_response:
                        return error_response
                    case Path() as project_dir:
                        question = "What are the main topics?"
                        search = get_search(request)
                        engine = find_engine_from_query(request)
                        match engine:
                            case Engine.GRAPHRAG:
                                search_params = ContextParameters(
                                    query=question,
                                    project_dir=project_dir,
                                    context_size=cfg.local_context_max_tokens,
                                )
                                promise = (
                                    rag_local
                                    if search == Search.LOCAL.value
                                    else rag_global
                                )
                                response = await promise(search_params)
                            case Engine.LIGHTRAG:
                                response = await lightrag_search(
                                    project_dir, question, search
                                )
                        return web.Response(
                            text=HTML_CONTENT.format(
                                question=question, response=markdown(response)
                            ),
                            content_type="text/html",
                        )

    return await handle_error(handle_request, request=request)


DEFAULT_QUESTION = "What are the main topics?"


@routes.post("/protected/project/upload_index")
async def upload_index(request: web.Request) -> web.Response:
    """
    File Upload and Index
    ---
    summary: Uploads a files with a knowledge base for a specific tennant
    tags:
      - project
    security:
      - bearerAuth: []
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
                description: The zip file with the text files to be uploaded.
              project:
                type: string
                description: The name of the project
              engine:
                type: string
                description: The type of engine used to run the RAG system
                enum: [graphrag, lightrag]
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
        project = body["project"]
        engine_str = body["engine"]
        project = re.sub(r"[^a-z0-9_-]", "_", project.lower())
        match extract_tennant_folder(request):
            case Response() as error_response:
                return error_response
            case Path() as tennant_folder:
                if file_name is not None and file_name.lower().endswith(".zip"):
                    uploaded_file: Path = tennant_folder / file_name
                    write_uploaded_file(file, uploaded_file)
                    saved_files.append(uploaded_file)
                if (file_length := len(saved_files)) == 0:
                    return web.json_response(
                        {"error": "No file was uploaded"}, status=400
                    )
                # Extract the zip file
                engine = find_engine(engine_str)
                project_folder: Path = find_project_folder(
                    tennant_folder, engine, project
                )
                clear_rag(project_folder)
                try:
                    unzip_file(project_folder, saved_files[0])
                except zipfile.BadZipFile:
                    return web.json_response(
                        {"error": "Uploaded file is not a valid zip file"}, status=400
                    )
                except Exception as e:
                    return web.json_response(
                        {"error": f"Failed to process uploaded file: {e}"}, status=500
                    )
                match engine:
                    case Engine.GRAPHRAG:
                        await acreate_graph_rag(True, project_folder)
                    case Engine.LIGHTRAG:
                        await acreate_lightrag(True, project_folder)
                return web.json_response(
                    {
                        "message": f"{file_length} file{"" if len(saved_files) == 0 else ""} uploaded, extracted and indexed from {project_folder}."
                    },
                    status=200,
                )
            case _:
                return web.json_response(
                    {"error": "Could not extract tennant folder."}, status=500
                )

    return await handle_error(
        handle_request, request=request, response_format=Format.JSON.value
    )


@routes.get("/protected/project/query")
async def query(request: web.Request) -> web.Response:
    """
    Query RAG index
    ---
    summary: returns the response to a query from an LLM
    tags:
      - project
    security:
      - bearerAuth: []
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag]
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
          enum: [json, html, markdown]
      - name: search
        in: query
        required: false
        description: The type of the search (local, global, drift). Drift only works with graphrag.
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
      '400':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              status: "error"
              message: "No project found"
    """

    async def handle_request(request: web.Request) -> web.Response:
        match extract_tennant_folder(request):
            case Response() as error_response:
                return error_response
            case Path() as tennant_folder:
                match handle_project_folder(request, tennant_folder):
                    case Response() as error_response:
                        return error_response
                    case Path() as project_dir:
                        format = request.rel_url.query.get("format", Format.JSON.value)
                        search = get_search(request)
                        context_params = create_context_parameters(
                            request.rel_url, project_dir
                        )
                        engine = find_engine_from_query(request)
                        match engine:
                            case Engine.GRAPHRAG:
                                match search:
                                    case Search.GLOBAL:
                                        response = await rag_global(context_params)
                                    case Search.DRIFT:
                                        response = await rag_drift(context_params)
                                    case _:
                                        response = await rag_local(context_params)
                            case Engine.LIGHTRAG:
                                match search:
                                    case Search.GLOBAL | Search.LOCAL:
                                        response = await lightrag_search(
                                            project_dir, context_params.query, search
                                        )
                                    case _:
                                        raise web.HTTPBadRequest(
                                            text="LightRAG does not support local search"
                                        )
                        match format:
                            case Format.HTML:
                                return web.Response(
                                    text=HTML_CONTENT.format(
                                        question=context_params.query,
                                        response=markdown(response),
                                    ),
                                    content_type="text/html",
                                )
                            case Format.MARKDOWN:
                                return web.Response(
                                    text=response,
                                    content_type="text/plain",
                                )
                            case Format.JSON:
                                return web.json_response(
                                    {
                                        "question": context_params.query,
                                        "response": response,
                                    }
                                )
                        raise web.HTTPBadRequest(
                            text="Please make sure the format is specified."
                        )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/context")
async def context(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the context used by on a specific request
    tags:
      - project
    security:
      - bearerAuth: []
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag]
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
        description: The type of the search (local, global). Drift only works with graphrag.
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
      '400':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              status: "error"
              message: "No project found"
    """

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                search = request.rel_url.query.get("search", Search.LOCAL.value)
                use_context_records = (
                    request.rel_url.query.get("use_context_records", "false") == "true"
                )
                context_params = create_context_parameters(request.rel_url, project_dir)
                engine = find_engine_from_query(request)
                sources = []

                def process_records(records: Optional[dict]):
                    if not records:
                        return {}
                    return (
                        {kv[0]: kv[1].to_dict() for kv in records.items()}
                        if use_context_records
                        else None
                    )

                match engine:
                    case Engine.GRAPHRAG:
                        match search:
                            case Search.GLOBAL:
                                context_builder_result = await rag_global_build_context(
                                    context_params
                                )
                            case Search.ALL:
                                context_builder_result = await rag_combined_context(
                                    context_params
                                )
                            case Search.DRIFT:
                                context_builder_result = await rag_drift_context(
                                    context_params
                                )
                            case _:
                                context_builder_result = rag_local_build_context(
                                    context_params
                                )
                                if (
                                    context_builder_result.local_context_records[
                                        "sources"
                                    ]
                                    is not None
                                ):
                                    sources = list(
                                        set(
                                            context_builder_result.local_context_records[
                                                "sources"
                                            ][
                                                "document_title"
                                            ].tolist()
                                        )
                                    )
                        return web.json_response(
                            {
                                "context_text": context_builder_result.context_text,
                                "sources": sources,
                                "local_context_records": process_records(
                                    context_builder_result.local_context_records
                                ),
                                "global_context_records": process_records(
                                    context_builder_result.global_context_records
                                ),
                            }
                        )
                    case Engine.LIGHTRAG:
                        match search:
                            case Search.GLOBAL | Search.LOCAL | Search.ALL:
                                actual_search = search if search is not Search.ALL else "hybrid"
                                context_builder_result = await lightrag_search(
                                    project_dir, context_params.query, actual_search, True
                                )
                                return web.json_response(
                                    {
                                        "context_text": context_builder_result,
                                    }
                                )
                            case _:
                                raise web.HTTPBadRequest(
                                    text="LightRAG does not support local search"
                                )

    return await handle_error(handle_request, request=request)


@routes.options("/protected/projects")
async def list_projects_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/projects")
async def list_projects(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns all projects of a tennant
    tags:
      - project
    security:
      - bearerAuth: []
    responses:
      '200':
        description: Expected response to a valid request. Lists the projects of a tennant
      '400':
        description: Bad Request - No projects found
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    async def handle_request(request: web.Request) -> web.Response:
        match extract_tennant_folder(request):
            case Response() as error_response:
                return error_response
            case Path() as tennant_dir:
                projects = project_listing(tennant_dir)
                return web.json_response(projects.model_dump(), headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request)


@routes.delete("/protected/project/delete_index")
async def delete_index(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the response to a query from an LLM
    tags:
      - project
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag]
    security:
      - bearerAuth: []
    responses:
      '200':
        description: Expected response to a valid request. Tells whether the project was deleted or not.
      '400':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                deleted = clear_rag(project_dir)
                return web.json_response(
                    {
                        "deleted": deleted,
                    }
                )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/download/input")
async def download_input(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a file with the content of the input folder
    tags:
      - project
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A zip file with the content of the input folder.
    """

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                input_path = project_dir / "input"
                if not input_path.exists():
                    return invalid_response(
                        "No tennant information",
                        "No tennant information available in request",
                    )
                # Zip the input folder and return it.
                zip_file = zip_input(input_path)
                return web.FileResponse(
                    zip_file,
                    headers={
                        "CONTENT-DISPOSITION": f'attachment; filename="{zip_file.name}"'
                    },
                )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/download/single_file")
async def download_single_file(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a file with the content of the input folder
    tags:
      - project
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: file
        in: query
        required: true
        description: The file name
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A file as an attachment
      '404':
        description: Bad Request - No file found.
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No file found"
              error_description: "The file does not exist"
    """

    async def handle_request(request: web.Request) -> web.Response:

        def create_file_nout_found_error(file_name: str, input_dir: Path):
            possible_files = [
                file.name for file in list(input_dir.glob("**/*")) if file.is_file()
            ]
            return invalid_response(
                "No files found",
                f"The file' {file_name}' does not exist. Possible files: {possible_files[:10]}",
            )

        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                file_name = request.rel_url.query.get("file", None)
                match file_name:
                    case None:
                        return invalid_response(
                            "No file available",
                            "Please specify a file name",
                        )
                    case _:
                        input_dir = project_dir / "input"
                        file_paths = [
                            file
                            for file in list(input_dir.glob("**/*"))
                            if file.name.lower() == file_name.lower() and file.is_file()
                        ]
                        length = len(file_paths)
                        if length == 0:
                            return create_file_nout_found_error(file_name, input_dir)
                        elif length == 1:
                            file_path = file_paths[0]
                            return web.FileResponse(
                                file_path,
                                headers={
                                    "CONTENT-DISPOSITION": f'attachment; filename="{file_path.name}"'
                                },
                            )
                        else:
                            # Create zip file in memory
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(
                                zip_buffer, "w", zipfile.ZIP_DEFLATED
                            ) as zip_file:
                                for i, file_path in enumerate(file_paths):
                                    zip_file.write(
                                        file_path,
                                        arcname=f"{file_path.stem}_{i + 1}.{file_path.suffix}",
                                    )

                            # Seek to start of buffer
                            zip_buffer.seek(0)

                            return web.Response(
                                body=zip_buffer.getvalue(),
                                headers={
                                    "CONTENT-TYPE": "application/zip",
                                    "CONTENT-DISPOSITION": f'attachment; filename="{file_name}.zip"',
                                },
                            )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/topics")
async def topics(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a list of topics based on the level
    tags:
      - project
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: levels
        in: query
        required: true
        description: Comma separated list of integers representing the level with 0 as the highest abstraction level. Example '0,1'
        schema:
          type: string
      - name: format
        in: query
        required: false
        description: The format of the output (json, html)
        schema:
          type: string
          enum: [json, html]
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A list of topics matching the specified levels either in HTML of JSON
    """

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                levels_str = request.rel_url.query.get("levels", "0")
                levels = [int(level.strip()) for level in levels_str.split(",")]
                community_df = prepare_community_extraction(project_dir, levels)
                community_list = [
                    c
                    for c in zip(
                        community_df["title_y"],
                        community_df["summary"],
                        community_df["rank"],
                        community_df["level"],
                    )
                ]
                format = request.rel_url.query.get("format", "json")
                match format:
                    case Format.HTML:
                        html_header = "\n".join(
                            [
                                f"<th>{t}</th>"
                                for t in ["Title", "Summary", "Rank", "Level"]
                            ]
                        )
                        html_list = [
                            f"<tr><td>{c[0]}</td><td>{c[1]}</td><td>{c[2]}</td><td>{c[3]}</td></tr>"
                            for c in zip(
                                community_df["title_y"],
                                community_df["summary"],
                                community_df["rank"],
                                community_df["level"],
                            )
                        ]
                        html_table = f"""<table><tr>{html_header}</tr>{"\n".join(html_list)}</table>"""
                        return web.Response(
                            text=HTML_CONTENT.format(
                                question="Topics", response=html_table
                            ),
                            content_type="text/html",
                        )
                    case _:
                        return web.json_response(community_list)
                return web.json_response(community_list)

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/topics_network")
async def topics_network_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/topics_network")
async def topics_network(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a file with the community graph structure in nexf format.
    tags:
      - graph
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A file representing the graph of community nodes.
    """

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                graph_file = generate_gexf_file(project_dir)
                return send_gexf_file(project_dir, graph_file)

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/topics_network/community/{id}")
async def topics_network_community_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/topics_network/community/{id}")
async def topics_network_community(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the details of a single community
    tags:
      - graph
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: id
        in: path
        required: true
        description: The community id
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A file representing the graph of community nodes.
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: string
                title:
                  type: string
                summary:
                  type: string
      '404':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    async def handle_request(request: web.Request) -> web.Response:
        async def process_community(project_dir: Path, community_id: str):
            community_report = find_community(project_dir, community_id)
            if community_report:
                return web.json_response(
                    community_report.model_dump(), headers=CORS_HEADERS
                )
            else:
                return invalid_response(
                    "Cannot find community report",
                    "Please specify another community id.",
                    status=404,
                )

        return await process_community_query(request, process_community)

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/topics_network/community_entities/{id}")
async def topics_network_community_entities_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/topics_network/community_entities/{id}")
async def topics_network_community_entities(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the entities of a single community
    tags:
      - graph
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: id
        in: path
        required: true
        description: The community id
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A file representing the graph with the entities of a community.
      '404':
        description: Bad Request - No community or project found.
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    async def handle_request(request: web.Request) -> web.Response:
        async def process_community(project_dir: Path, community_id: str):
            gex_file = generate_entities_digraph_gexf_file(
                project_dir, int(community_id)
            )
            if gex_file:
                return send_gexf_file(project_dir, gex_file)
            else:
                return invalid_response(
                    "Cannot find community report",
                    "Please specify another community id.",
                    status=404,
                )

        return await process_community_query(request, process_community)

    return await handle_error(handle_request, request=request)


def create_context_parameters(url: URL, project_dir: Path) -> ContextParameters:
    question = url.query.get("question", DEFAULT_QUESTION)
    context_size = url.query.get("context_size", cfg.local_context_max_tokens)
    return ContextParameters(
        query=question,
        project_dir=project_dir,
        context_size=context_size,
    )


logger.info("project_server.py loaded")

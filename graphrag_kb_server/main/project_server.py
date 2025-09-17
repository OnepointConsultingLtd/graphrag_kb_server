import zipfile
import asyncio
import io
import re
import uuid
from pathlib import Path
from typing import Optional, Callable, Awaitable

from aiohttp import web

from yarl import URL
from markdown import markdown
from aiohttp.web import Response
from asyncer import asyncify

from graphrag_kb_server.model.rag_parameters import (
    ContextParameters,
    QueryParameters,
    ContextFormat,
)
from graphrag_kb_server.model.context import Search
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopicsRequest
from graphrag_kb_server.config import cfg
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.service.graphrag.query import rag_local_simple
from graphrag_kb_server.service.graphrag.query import (
    rag_local_build_context,
    rag_global_build_context,
    rag_combined_context,
    rag_drift_context,
)
from graphrag_kb_server.service.project import (
    clear_rag,
    acreate_graph_rag,
    list_projects as project_listing,
    write_project_file,
    single_project_status,
)
from graphrag_kb_server.service.zip_service import zip_input
from graphrag_kb_server.service.question_generation_service import (
    generate_questions_from_topics,
)
from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.main.project_request_functions import (
    extract_tennant_folder,
    handle_project_folder,
)
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
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_visualization import (
    generate_lightrag_graph_visualization,
)
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
    get_sorted_centrality_scores_as_xls,
)
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    extract_entity_types,
    create_network_from_project_dir,
    extract_entity_types_excel,
)
from graphrag_kb_server.service.lightrag.lightrag_clustering import (
    generate_communities_excel,
    generate_communities_json,
)
from graphrag_kb_server.main.simple_template import HTML_CONTENT
from graphrag_kb_server.main.query_support import execute_query
from graphrag_kb_server.service.lightrag.lightrag_summary import get_summary
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_communities_gexf_for_project,
    find_community_lightrag,
)
from graphrag_kb_server.service.file_find_service import find_original_file
from graphrag_kb_server.service.topic_generation import (
    generate_topics,
    convert_topics_to_pandas,
)
from graphrag_kb_server.model.topics import TopicsRequest, QuestionsQuery
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.cag.cag_support import (
    acreate_cag,
    INITIAL_CONVERSATION_ID,
    cag_get_response,
)
from graphrag_kb_server.main.project_request_functions import extract_engine_limit
from graphrag_kb_server.service.graphrag.related_topics import (
    get_related_topics_graphrag,
)
from graphrag_kb_server.service.lightrag.lightrag_related_topics import (
    get_related_topics_lightrag,
)
from graphrag_kb_server.service.topics_post_processing import (
    post_process_topics,
    deduplicate_topics,
)

routes = web.RouteTableDef()


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
async def index(_: web.Request) -> web.Response:
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
        description: The type of the search (local, global). Only applicable for LightRAG and GraphRAG.
        schema:
          type: string
          enum: [local, global]
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag, cag]
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
                        search_params = ContextParameters(
                            query=question,
                            project_dir=project_dir,
                            context_size=cfg.local_context_max_tokens,
                        )
                        match engine:
                            case Engine.GRAPHRAG:
                                response = await rag_local_simple(search_params)
                            case Engine.LIGHTRAG:
                                query_params = QueryParameters(
                                    format=Format.HTML.value,
                                    search=search,
                                    engine=Engine.LIGHTRAG.value,
                                    context_params=search_params,
                                )
                                chat_response = await lightrag_search(query_params)
                                response = chat_response.response
                            case Engine.CAG:
                                response = await cag_get_response(
                                    project_dir, str(uuid.uuid4()), question
                                )
                        return web.Response(
                            text=HTML_CONTENT.format(
                                question=question, response=markdown(response)
                            ),
                            content_type="text/html",
                        )

    return await handle_error(handle_request, request=request)


DEFAULT_QUESTION = "What are the main topics?"


@routes.options("/protected/project/upload_index")
async def upload_index_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


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
                enum: [graphrag, lightrag, cag]
              incremental:
                type: boolean
                default: false
                description: Whether to update the existing index or create a new one. Works only for LightRAG and has no effect on GraphRAG.
              asynchronous:
                type: boolean
                default: false
                description: Whether to run the indexing asynchronously.
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

    async def handle_project_indexing(
        project_folder: Path, incremental: bool, engine: Engine, saved_files: list[Path]
    ):
        try:
            write_project_file(project_folder, IndexingStatus.PREPARING)
            await unzip_file(project_folder, saved_files[0])
            write_project_file(project_folder, IndexingStatus.IN_PROGRESS)
        except zipfile.BadZipFile:
            write_project_file(project_folder, IndexingStatus.FAILED)
            logger.error("Uploaded file is not a valid zip file")
            return
        except Exception as e:
            write_project_file(project_folder, IndexingStatus.FAILED)
            logger.error(f"Failed to process uploaded file: {e}")
            return

        try:
            match engine:
                case Engine.GRAPHRAG:
                    await acreate_graph_rag(True, project_folder)
                case Engine.LIGHTRAG:
                    await acreate_lightrag(
                        True, project_folder, incremental, saved_files[0]
                    )
                case Engine.CAG:
                    await acreate_cag(project_folder, INITIAL_CONVERSATION_ID)
            write_project_file(project_folder, IndexingStatus.COMPLETED)
        except Exception as e:
            write_project_file(project_folder, IndexingStatus.FAILED)
            logger.error(f"Failed to process uploaded file: {e}")
            return

    async def handle_request(request: web.Request) -> web.Response:
        saved_files = []
        body = request["data"]["body"]
        file = body["file"]
        file_name = body["file_name"]
        engine_str = body["engine"]
        incremental = body["incremental"]
        asynchronous = body["asynchronous"]
        sanitized_project_name = re.sub(r"[^a-z0-9_-]", "_", body["project"].lower())
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
                        {"error": "No file was uploaded"},
                        status=400,
                        headers=CORS_HEADERS,
                    )
                # Extract the zip file
                engine = find_engine(engine_str)
                project_folder: Path = find_project_folder(
                    tennant_folder, engine, sanitized_project_name
                )
                if engine in [Engine.GRAPHRAG, Engine.CAG] or not incremental:
                    clear_rag(project_folder)

                if asynchronous:
                    asyncio.create_task(
                        handle_project_indexing(
                            project_folder, incremental, engine, saved_files
                        )
                    )
                else:
                    await handle_project_indexing(
                        project_folder, incremental, engine, saved_files
                    )
                return web.json_response(
                    {
                        "message": (
                            f"{file_length} file{"" if len(saved_files) == 0 else ""} uploaded, extracted and indexed from {project_folder}."
                            if not asynchronous
                            else "Indexing in progress..."
                        )
                    },
                    status=200,
                    headers=CORS_HEADERS,
                )
            case _:
                return web.json_response(
                    {"error": "Could not extract tennant folder."},
                    status=500,
                    headers=CORS_HEADERS,
                )

    return await handle_error(
        handle_request, request=request, response_format=Format.JSON.value
    )


@routes.options("/protected/project/query")
async def query_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


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
          enum: [graphrag, lightrag, cag]
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
          enum: [local, global, all, drift, naive]
      - name: context_size
        in: query
        required: false
        description: The size of the context, like eg 14000
        schema:
          type: integer
          format: int32
      - name: conversation_id
        in: query
        required: false
        description: The conversation id. Only for CAG
        schema:
          type: string
          default: 1234567890
    responses:
      '200':
        description: The response to the query in either json, html or markdown format
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
                        conversation_id = request.rel_url.query.get(
                            "conversation_id", str(uuid.uuid4())
                        )
                        return await execute_query(
                            QueryParameters(
                                format=format,
                                search=search,
                                engine=engine,
                                context_params=context_params,
                                conversation_id=conversation_id,
                            )
                        )

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/chat")
async def chat_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/project/chat")
async def chat(request: web.Request) -> web.Response:
    """
    Chat with the RAG index
    ---
    summary: returns the response to a chat from an LLM using the RAG index
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
          enum: [graphrag, lightrag, cag]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              question:
                type: string
                description: The question for which the context is retrieved. For example 'What are the main topics?'
                default: "What are the main topics?"
              search:
                type: string
                description: The type of the search (local, global, drift). Drift only works with graphrag.
                enum: [local, global, all, drift, naive]
              format:
                type: string
                description: The format of the output (json, html, markdown)
                enum: [json, html, markdown]
              context_size:
                type: integer
                description: The size of the context, like eg 14000
                format: int32
                default: 14000
              system_prompt_additional:
                type: string
                description: Additional instructions to the LLM. This will not override the original system prompt.
                default: ""
              hl_keywords:
                type: array
                items:
                  type: string
                description: High-level keywords to add to the query.
              ll_keywords:
                type: array
                items:
                  type: string
                description: Low-level keywords to add to the query.
              include_context:
                type: boolean
                description: Whether to include the context in the response.
                default: false
              include_context_as_text:
                type: boolean
                description: Whether to include the context as text in the response.
                default: false
              structured_output:
                type: boolean
                description: Whether to use structured output.
                default: false
              conversation_id:
                type: string
                description: The conversation id. Only for CAG
                default: 1234567890
              chat_history:
                type: array
                items:
                  type: object
                description: The chat history.
    responses:
      '200':
        description: The response to the query in either json
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
                        body = request["data"]["body"]
                        (
                            format,
                            search,
                            engine,
                            question,
                            system_prompt_additional,
                            context_size,
                            hl_keywords,
                            ll_keywords,
                            include_context,
                            include_context_as_text,
                            structured_output,
                            chat_history,
                            conversation_id,
                        ) = (
                            body.get("format", Format.JSON.value),
                            body["search"],
                            find_engine_from_query(request),
                            body["question"],
                            body["system_prompt_additional"],
                            body["context_size"],
                            body.get("hl_keywords", []),
                            body.get("ll_keywords", []),
                            body.get("include_context", False),
                            body.get("include_context_as_text", False),
                            body.get("structured_output", False),
                            body.get("chat_history", []),
                            body.get("conversation_id", str(uuid.uuid4())),
                        )
                        context_params = ContextParameters(
                            query=question,
                            project_dir=project_dir,
                            context_size=context_size,
                        )
                        return await execute_query(
                            QueryParameters(
                                format=format,
                                search=search,
                                engine=engine,
                                context_params=context_params,
                                system_prompt_additional=system_prompt_additional,
                                hl_keywords=hl_keywords,
                                ll_keywords=ll_keywords,
                                include_context=include_context,
                                include_context_as_text=include_context_as_text,
                                structured_output=structured_output,
                                chat_history=chat_history,
                                conversation_id=conversation_id,
                            )
                        )

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/topics")
async def project_topics_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/topics")
async def project_topics(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the main topics of a project
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
          enum: [graphrag, lightrag, cag]
      - name: limit
        in: query
        required: false
        description: The number of topics to return
        schema:
          type: integer
          format: int32
          default: 20
      - name: add_questions
        in: query
        required: false
        description: Whether to add questions to the topics. Not implemented yet.
        schema:
          type: boolean
          default: false
      - name: entity_type_filter
        in: query
        required: false
        description: The entity type to filter by. Only used for LightRAG
        schema:
          type: string
          default: category
      - name: format
        in: query
        required: false
        description: The format of the output (json, csv)
        schema:
          type: string
          enum: [json, csv]
          default: json
      - name: deduplicate_topics
        in: query
        required: false
        description: Whether to deduplicate the topics.
        schema:
          type: boolean
          default: false
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
                engine, limit = extract_engine_limit(request)
                add_questions = (
                    request.rel_url.query.get("add_questions", "false") == "true"
                )
                entity_type_filter = request.rel_url.query.get("entity_type_filter", "")
                deduplicate_topics_param = (
                    request.rel_url.query.get("deduplicate_topics", "false") == "true"
                )
                topics = await generate_topics(
                    TopicsRequest(
                        project_dir=project_dir,
                        engine=engine,
                        limit=limit,
                        add_questions=add_questions,
                        entity_type_filter=entity_type_filter,
                        deduplicate_topics=deduplicate_topics_param,
                    )
                )
                format = request.rel_url.query.get("format", Format.JSON.value)
                match format:
                    case Format.JSON:
                        return web.json_response(
                            topics.model_dump(), headers=CORS_HEADERS
                        )
                    case Format.CSV:
                        df = convert_topics_to_pandas(topics)
                        return web.Response(
                            text=df.to_csv(index=False),
                            headers={
                                **CORS_HEADERS,
                                "CONTENT-DISPOSITION": f'attachment; filename="{project_dir.name}_topics.csv"',
                            },
                        )
                    case _:
                        return invalid_response("Invalid format", "Invalid format")
            case _:
                return invalid_response("No project found", "No project found")

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/questions")
async def project_questions_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/project/questions")
async def project_questions(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns generated questions for a project based on the most popular topics
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
          enum: [graphrag, lightrag, cag]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              topics:
                type: array
                items:
                  type: string
                description: The topics filter
                default: []
              text:
                type: string
                description: The text to generate questions for
                default: ""
              topic_limit:
                type: integer
                format: int32
                description: The number of topics from which to generate questions
                default: 10
              entity_type_filter:
                type: string
                description: The entity type to filter by. Only used for LightRAG
                default: category
              format:
                type: string
                description: The format of the output (json, csv)
                enum: [json, csv]
                default: json
              system_prompt:
                type: string
                description: The system prompt to use for the question generation. This will override the default system prompt.
                default: ""
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
                body = request["data"]["body"]
                engine = find_engine_from_query(request)
                limit = body.get("topic_limit", 10)
                entity_type_filter = body.get("entity_type_filter", "category")
                topics = body.get("topics", "")
                text = body.get("text", "")
                topic_questions = await generate_questions_from_topics(
                    QuestionsQuery(
                        project_dir=project_dir,
                        engine=engine,
                        limit=limit,
                        entity_type_filter=entity_type_filter,
                        topics=topics,
                        text=text,
                        system_prompt=body.get("system_prompt", ""),
                    )
                )
                format = request.rel_url.query.get("format", Format.JSON.value)
                match format:
                    case Format.JSON:
                        return web.json_response(
                            topic_questions.model_dump(), headers=CORS_HEADERS
                        )
                    case Format.CSV:
                        df = convert_topics_to_pandas(topic_questions)
                        return web.Response(
                            text=df.to_csv(index=False),
                            headers={
                                **CORS_HEADERS,
                                "CONTENT-DISPOSITION": f'attachment; filename="{project_dir.name}_questions.csv"',
                            },
                        )
                    case _:
                        return invalid_response("Invalid format", "Invalid format")

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/related_topics")
async def project_related_topics_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/project/related_topics")
async def project_related_topics(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the related topics of a project
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
          enum: [graphrag, lightrag, cag]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - source
            properties:
              source:
                type: string
                description: The source entity to find related entities for
              text:
                type: string
                description: The text to find related entities for
              samples:
                type: integer
                format: int32
                default: 50000
                description: The number of random walk samples to perform
              path_length:
                type: integer
                format: int32
                default: 5
                description: The length of each random walk path
              restart_prob:
                type: number
                default: 0.15
                description: The probability of restarting the random walk at the source node
              runs:
                type: integer
                format: int32
                default: 10
                description: The number of independent runs to average results
              limit:
                type: integer
                format: int32
                default: 8
                description: The number of topics to return
              topics_prompt:
                type: string
                description: The prompt to post process the generated topics.
                default: ""
              deduplicate_topics:
                type: boolean
                description: Whether to deduplicate the topics.
                default: false
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

    async def get_related_topics(
        engine: Engine, similarity_topics: SimilarityTopicsRequest
    ) -> SimilarityTopics | None:
        similarity_topics_result = None
        match engine:
            case Engine.GRAPHRAG:
                similarity_topics_result = await asyncify(get_related_topics_graphrag)(
                    similarity_topics
                )
            case Engine.LIGHTRAG:
                similarity_topics_result = await get_related_topics_lightrag(
                    similarity_topics
                )
            case _:
                # No implementation for CAG yet
                return None
        if similarity_topics_result is not None:
            if similarity_topics.deduplicate_topics:
                similarity_topics_result = await deduplicate_topics(
                    similarity_topics_result
                )
            if similarity_topics.topics_prompt:
                similarity_topics_result = await post_process_topics(
                    similarity_topics_result, similarity_topics.topics_prompt
                )
        return similarity_topics_result

    async def handle_request(request: web.Request) -> web.Response:
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                try:
                    body = await request.json()
                    source = body.get("source", "AI")
                    text = body.get("text", "")
                    samples = body.get("samples", 50000)
                    path_length = body.get("path_length", 5)
                    restart_prob = body.get("restart_prob", 0.15)
                    runs = body.get("runs", 10)
                    limit = body.get("limit", 8)
                    topics_prompt = body.get("topics_prompt", "")
                    deduplicate_topics = body.get("deduplicate_topics", False)
                    engine = find_engine_from_query(request)

                    similarity_topics = SimilarityTopicsRequest(
                        project_dir=project_dir,
                        source=source,
                        text=text,
                        samples=samples,
                        engine=engine,
                        path_length=path_length,
                        restart_prob=restart_prob,
                        k=limit,
                        runs=runs,
                        topics_prompt=topics_prompt,
                        deduplicate_topics=deduplicate_topics,
                    )
                    # Run the CPU-intensive work in a thread pool
                    topics = await get_related_topics(engine, similarity_topics)
                    if topics is None:
                        return invalid_response(
                            "No topics found", "No topics found", status=404
                        )
                    return web.json_response(topics.model_dump(), headers=CORS_HEADERS)
                except ValueError as e:
                    return invalid_response("Invalid engine value", str(e))
                except Exception as e:
                    return invalid_response("Invalid request body", str(e))
            case _:
                return invalid_response("No project found", "No project found")

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
        description: Whether to output the context records or not. (Applies only to GraphRAG)
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
      - name: keywords
        in: query
        required: false
        description: If true appends the keywords to the context. Only for LightRAG
        schema:
          type: boolean
          default: false
      - name: format
        in: query
        required: false
        description: The format of the output (json_string, json, json_string_with_json). "json" only works for Lightrag for now.
        schema:
          type: string
          enum: [json_string, json, json_string_with_json]
          default: json_string
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
                                keywords = (
                                    request.rel_url.query.get("keywords", "false")
                                    == "true"
                                )
                                actual_search = (
                                    search if search != Search.ALL else "hybrid"
                                )
                                query_params = QueryParameters(
                                    format=Format.MARKDOWN.value,
                                    search=actual_search,
                                    engine=Engine.LIGHTRAG.value,
                                    context_params=context_params,
                                    include_context=context_params.context_format
                                    == ContextFormat.JSON,
                                    keywords=keywords,
                                    context_format=context_params.context_format,
                                )
                                context_builder_result = await lightrag_search(
                                    query_params,
                                    True,
                                )
                                extra_context = (
                                    {
                                        "hl_keywords": context_builder_result.hl_keywords,
                                        "ll_keywords": context_builder_result.ll_keywords,
                                    }
                                    if keywords
                                    else {}
                                )
                                match context_params.context_format:
                                    case (
                                        ContextFormat.JSON
                                        | ContextFormat.JSON_STRING_WITH_JSON
                                    ):
                                        context_data = {
                                            "entities_context": context_builder_result.entities_context,
                                            "relations_context": context_builder_result.relations_context,
                                            "text_units_context": context_builder_result.text_units_context,
                                        }
                                        if (
                                            context_params.context_format
                                            == ContextFormat.JSON_STRING_WITH_JSON
                                        ):
                                            return web.json_response(
                                                {
                                                    **context_data,
                                                    "context_text": context_builder_result.context,
                                                }
                                            )
                                        else:
                                            return web.json_response(
                                                {
                                                    "context_text": context_builder_result.context,
                                                }
                                            )
                                    case _:
                                        return web.json_response(
                                            {
                                                "context_text": context_builder_result.context,
                                                **extra_context,
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


@routes.options("/protected/project/status/{engine}/{project_name}")
async def project_status_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/status/{engine}/{project_name}")
async def project_status(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the status information of a project
    tags:
      - project
    security:
      - bearerAuth: []
    parameters:
      - name: engine
        in: path
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag, cag]
      - name: project_name
        in: path
        required: true
        description: The project name
        schema:
          type: string
    responses:
      '200':
        description: Used to return the information about a project.
        content:
          application/json:
            example:
              project_name: "project_name"
              indexing_status: "completed"
              updated_timestamp: "2021-01-01T00:00:00Z"
              input_files: ["file1.txt", "file2.txt"]
      '400':
        description: Bad Request - No project found
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    def _project_not_found(project_dir: Path) -> web.Response:
        return web.json_response(
            {"error": f"Project not found: {project_dir}"},
            status=404,
            headers=CORS_HEADERS,
        )

    async def handle_request(request: web.Request) -> web.Response:
        match extract_tennant_folder(request):
            case Response() as error_response:
                return error_response
            case Path() as tennant_dir:
                engine = request.match_info.get("engine", None)
                project_name = request.match_info.get("project_name", None)
                project_dir = tennant_dir / engine / project_name
                if not project_dir.exists():
                    return _project_not_found(project_dir)
                project = single_project_status(project_dir)
                if not project:
                    return _project_not_found(project_dir)
                return web.json_response(project.model_dump(), headers=CORS_HEADERS)
            case _:
                return invalid_response(
                    "No tennant information",
                    "No tennant information available in request",
                )

    return await handle_error(handle_request, request=request)


@routes.options("/protected/project/delete_index")
async def delete_index_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


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
          enum: [graphrag, lightrag, cag]
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
                return web.json_response({"deleted": deleted}, headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/download/project")
async def download_project(request: web.Request) -> web.Response:
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
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          enum: [graphrag, lightrag, cag]
      - name: input_only
        in: query
        required: true
        description: Whether only the input is to be downloaded or the whole folder
        schema:
          type: boolean
          default: true
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
                input_only = request.rel_url.query.get("input_only", "true") == "true"
                input_path = project_dir / INPUT_FOLDER if input_only else project_dir
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


@routes.options("/protected/project/download/single_file")
async def download_single_file_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/project/download/single_file")
async def download_single_file(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a file with the content of the input folder
    tags:
      - project
    security: []  # Empty security array indicates no authentication required
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
          enum: [graphrag, lightrag, cag]
      - name: file
        in: query
        required: true
        description: The file name
        schema:
          type: string
      - name: summary
        in: query
        required: false
        description: Whether to include the summary or the file content in the response. LightRAG only.
        schema:
          type: boolean
      - name: original_file
        in: query
        required: false
        description: Whether to include the original file content in the response.
        schema:
          type: boolean
      - name: token
        in: query
        required: false
        description: The token to use to access the file.
        schema:
          type: string
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

        def _create_file_not_found_error(file_name: str, input_dir: Path):
            possible_files = [
                file.name for file in list(input_dir.glob("**/*")) if file.is_file()
            ]
            return invalid_response(
                "No files found",
                f"The file' {file_name}' does not exist. Possible files: {possible_files[:10]}",
            )

        def _get_summary(project_dir: Path, file_path_str: str) -> web.FileResponse:
            summary = get_summary(project_dir, file_path_str)
            file_path = Path(file_path_str)
            if summary is not None and isinstance(summary, str):
                return web.Response(
                    body=summary.encode("utf-8"),
                    headers={
                        "CONTENT-DISPOSITION": f'attachment; filename="{file_path.stem}_summary{file_path.suffix}"',
                        **CORS_HEADERS,
                    },
                )

        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                file_name = request.rel_url.query.get("file", None)
                original_file = (
                    request.rel_url.query.get("original_file", "false") == "true"
                )
                match file_name:
                    case None:
                        return invalid_response(
                            "No file available",
                            "Please specify a file name",
                        )
                    case _:
                        summary = (
                            request.rel_url.query.get("summary", "false") == "true"
                        )
                        engine = request.rel_url.query.get("engine")
                        input_dir = project_dir / INPUT_FOLDER
                        if (
                            input_dir.resolve().as_posix()
                            in Path(file_name).resolve().as_posix()
                        ):
                            if summary and engine == "lightrag":
                                return _get_summary(project_dir, file_name)

                            if not original_file:
                                return web.FileResponse(
                                    file_name,
                                    headers={
                                        "CONTENT-DISPOSITION": f'attachment; filename="{Path(file_name).name}"',
                                        **CORS_HEADERS,
                                    },
                                )
                            else:
                                original_file_path = find_original_file(
                                    project_dir, Path(file_name)
                                )
                                if original_file_path:
                                    return web.FileResponse(
                                        original_file_path,
                                        headers={
                                            "CONTENT-DISPOSITION": f'attachment; filename="{original_file_path.name}"',
                                            **CORS_HEADERS,
                                        },
                                    )
                                else:
                                    return _create_file_not_found_error(
                                        file_name, input_dir
                                    )

                        file_paths = [
                            file
                            for file in list(input_dir.glob("**/*"))
                            if file.name.lower() == file_name.lower() and file.is_file()
                        ]
                        length = len(file_paths)
                        if length == 0:
                            return _create_file_not_found_error(file_name, input_dir)
                        elif length == 1:
                            file_path = file_paths[0]
                            if summary and engine == "lightrag":
                                return _get_summary(project_dir, file_path)

                            return web.FileResponse(
                                file_path,
                                headers={
                                    "CONTENT-DISPOSITION": f'attachment; filename="{file_path.name}"',
                                    **CORS_HEADERS,
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
                                    **CORS_HEADERS,
                                },
                            )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/topics_graphrag")
async def topics(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a list of topics based on the level
    tags:
      - graphrag-graph
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
      - graphrag-graph
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
          default: graphrag
          enum: [graphrag,lightrag]
      - name: recreate
        in: query
        required: false
        description: Whether to recreate the gexf file (applies only to lightrag)
        schema:
          type: boolean
          default: false
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A gexf file representing the graph of community nodes.
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                engine = request.rel_url.query.get("engine", "graphrag")
                recreate = request.rel_url.query.get("recreate", "false") == "true"
                match engine:
                    case "graphrag":
                        graph_file = generate_gexf_file(project_dir)
                    case "lightrag":
                        graph_file = await create_communities_gexf_for_project(
                            project_dir, recreate=recreate
                        )
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
      - graphrag-graph
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
      - name: engine
        in: query
        required: true
        description: The type of engine used to run the RAG system
        schema:
          type: string
          default: graphrag
          enum: [graphrag,lightrag]
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
            engine = request.rel_url.query.get("engine", "graphrag")
            match engine:
                case "graphrag":
                    community_report = find_community(project_dir, community_id)
                case "lightrag":
                    community_report = await find_community_lightrag(
                        project_dir, community_id
                    )
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
      - graphrag-graph
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
    format = url.query.get("format", ContextFormat.JSON_STRING.value)
    return ContextParameters(
        query=question,
        project_dir=project_dir,
        context_size=context_size,
        context_format=format,
    )


@routes.get("/protected/project/lightrag/graphvisualization")
async def lightrag_graph_visualization(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the graph visualization of the lightrag index
    tags:
      - lightrag-graph
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
          default: lightrag
          enum: [lightrag]
      - name: disposition
        in: query
        required: true
        description: How the file should be returned, either as attachment or inline
        schema:
          type: string
          default: attachment
          enum: [attachment, inline]
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A file representing the graph of the lightrag index.
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                graph_file = await asyncio.to_thread(
                    generate_lightrag_graph_visualization, project_dir
                )
                disposition = request.rel_url.query.get("disposition", "attachment")
                return web.FileResponse(
                    graph_file,
                    headers={
                        "CONTENT-DISPOSITION": f'{disposition}; filename="{graph_file.name}"'
                    },
                )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/lightrag/entity_types")
async def lightrag_entity_types(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: Returns the entity types of the lightrag index for a specific project.
    tags:
      - lightrag-graph
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
          default: lightrag
          enum: [lightrag]
      - name: format
        in: query
        required: true
        description: The format of the response
        schema:
          type: string
          default: json
          enum: [json, xls]
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A JSON response with the entity types and their counts.
        content:
          application/json:
            example:
              entity_types:
                - category: 10
                  organization: 20
                  geo: 30
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                format = request.rel_url.query.get("format", None)
                graph = await asyncio.to_thread(
                    create_network_from_project_dir, project_dir
                )
                match format:
                    case "json":
                        entity_types = extract_entity_types(graph)
                        return web.json_response(entity_types)
                    case "xls":
                        entity_types = extract_entity_types_excel(graph)
                        return web.Response(
                            body=entity_types,
                            headers={
                                "CONTENT-TYPE": "application/vnd.ms-excel",
                                "CONTENT-DISPOSITION": f'attachment; filename="{project_dir.stem}_entity_types.xlsx"',
                            },
                        )
                    case _:
                        return web.Response(
                            status=400,
                            text="Invalid format",
                        )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/lightrag/centrality")
async def lightrag_centrality(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: Returns the centrality scores of the lightrag index for a specific project.
    tags:
      - lightrag-graph
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
          default: lightrag
          enum: [lightrag]
      - name: format
        in: query
        required: true
        description: The format of the response
        schema:
          type: string
          default: json
          enum: [json, xls]
      - name: limit
        in: query
        required: false
        description: The maximum number of nodes to return
        schema:
          type: integer
          default: 20
      - name: category
        in: query
        required: false
        description: Category for filtering. Optional. Possible values are "category", "organization", "geo", "person", "equipment", "technology"
        schema:
          type: string
          default: category
          enum: ["category", "organization", "geo", "person", "equipment", "technology", "event", "economic_policy", "UNKNOWN"]
      - name: categories
        in: query
        required: false
        description: Categories for filtering as a comma separted list. Optional. If provided, the category parameter is ignored. Possible values are "category", "organization", "geo", "person", "equipment", "technology"
        schema:
          type: string
          default: category
    security:
      - bearerAuth: []
    responses:
      '200':
        description: A JSON response with the sorted centrality scores and corresponding node information or an Excel file with the centrality scores for each node.
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                format = request.rel_url.query.get("format", "json")
                limit = int(request.rel_url.query.get("limit", 20))
                match format:
                    case "json":
                        df = await asyncio.to_thread(
                            get_sorted_centrality_scores_as_pd, project_dir
                        )
                        category = request.rel_url.query.get("category", None)
                        categories = request.rel_url.query.get("categories", None)
                        if categories:
                            category_list = [
                                cat.strip() for cat in categories.split(",")
                            ]
                            df = df[df["entity_type"].isin(category_list)][:limit]
                        elif category:
                            df = df[df["entity_type"] == category][:limit]
                        return web.json_response(
                            df.to_dict(orient="records"), headers=CORS_HEADERS
                        )
                    case "xls":
                        excel_bytes = await asyncio.to_thread(
                            get_sorted_centrality_scores_as_xls, project_dir, limit
                        )
                        return web.Response(
                            body=excel_bytes,
                            headers={
                                "CONTENT-TYPE": "application/vnd.ms-excel",
                                "CONTENT-DISPOSITION": f'attachment; filename="{project_dir.stem}_centrality.xlsx"',
                                **CORS_HEADERS,
                            },
                        )

    return await handle_error(handle_request, request=request)


@routes.get("/protected/project/lightrag/communities_report")
async def lightrag_communities_report(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns a file with the community Excel file.
    tags:
      - lightrag-graph
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
          default: lightrag
          enum: [lightrag]
      - name: format
        in: query
        required: true
        description: The format of the response
        schema:
          type: string
          default: json
          enum: [json, xls]
      - name: max_cluster_size
        in: query
        required: true
        description: The maximum number of nodes in a community
        schema:
          type: integer
          default: 200
    security:
      - bearerAuth: []
    responses:
      '200':
        description: An Excel file with the communities.
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                max_cluster_size = request.rel_url.query.get("max_cluster_size", "10")
                format = request.rel_url.query.get("format", "json")
                match format:
                    case "json":
                        communities_dict = await generate_communities_json(
                            project_dir, int(max_cluster_size)
                        )
                        return web.json_response(communities_dict)
                    case "xls":
                        communities_file = await generate_communities_excel(
                            project_dir, int(max_cluster_size)
                        )
                        return web.FileResponse(
                            communities_file,
                            headers={
                                "CONTENT-DISPOSITION": f'attachment; filename="{project_dir}/{communities_file.name}"'
                            },
                        )
                    case _:
                        return web.Response(
                            status=400,
                            text="Invalid format",
                        )

    return await handle_error(handle_request, request=request)

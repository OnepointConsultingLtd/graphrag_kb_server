"""Endpoints to read and change the per-project settings (models and API keys).

Only administrators may use them: the access check is done by the authentication middleware
(see PROJECT_SETTINGS_PATH in multi_tennant_server). Secrets are never returned in clear.
"""

from pathlib import Path

from aiohttp import web

from graphrag_kb_server.logger import logger
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.main.multi_tennant_server import PROJECT_SETTINGS_PATH
from graphrag_kb_server.main.project_request_functions import extract_tennant_folder
from graphrag_kb_server.model.engines import find_engine_from_query
from graphrag_kb_server.model.error import ErrorCode
from graphrag_kb_server.service.crypto.secret_cipher import (
    ENCRYPTION_KEY_ENV_VARIABLE,
    SecretCipherError,
)
from graphrag_kb_server.service.project_settings_service import (
    EmbeddingModelLockedError,
    ProjectNotInDatabaseError,
    apply_settings_update,
    clear_project_settings,
    get_settings_view,
    parse_settings_update,
)

routes = web.RouteTableDef()

NOT_FOUND = 404
CONFLICT = 409
SERVICE_UNAVAILABLE = 503


def find_existing_project_dir(request: web.Request) -> web.Response | Path:
    """The folder of the project named in the request, which must already exist.

    Unlike the lookup used by the other endpoints, this never creates the folder, so a mistyped
    project name is an error and not a new empty project. Names with path separators are rejected.
    """
    match extract_tennant_folder(request):
        case web.Response() as error_response:
            return error_response
        case Path() as tennant_folder:
            project = request.rel_url.query.get("project")
            if not project:
                return invalid_response("No project", "Please specify the project name")
            if project in (".", "..") or project != Path(project).name:
                return invalid_response(
                    "Invalid project", "The project name must not contain a path"
                )
            project_dir = tennant_folder / find_engine_from_query(request).value / project
            if not project_dir.is_dir():
                return invalid_response(
                    "No project folder found", f"There is no project folder {project}"
                )
            return project_dir


def settings_response(settings_view) -> web.Response:
    return web.json_response(settings_view.model_dump(mode="json"), headers=CORS_HEADERS)


def encryption_unavailable_response(error: SecretCipherError) -> web.Response:
    """The server cannot encrypt or decrypt secrets: a configuration problem of the server."""
    logger.error(f"Project settings: {error}")
    return invalid_response(
        "Encryption not available",
        f"{error} Set {ENCRYPTION_KEY_ENV_VARIABLE} on the server.",
        ErrorCode.INVALID_INPUT,
        status=SERVICE_UNAVAILABLE,
    )


@routes.options(PROJECT_SETTINGS_PATH)
async def project_settings_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get(PROJECT_SETTINGS_PATH)
async def get_project_settings(request: web.Request) -> web.Response:
    """
    Returns the settings of a project
    ---
    summary: Returns the models and API keys used by a project and where each value comes from. Administrators only. Secrets are masked.
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
        required: false
        description: The engine of the project.
        schema:
          type: string
          enum: [lightrag, cag]
          default: lightrag
    security:
      - bearerAuth: []
    responses:
      '200':
        description: The settings. "source" tells whether the value is set by the project or comes from the server configuration (.env).
        content:
          application/json:
            schema:
              type: object
              properties:
                project:
                  type: string
                engine:
                  type: string
                settings:
                  type: array
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                      value:
                        type: string
                        nullable: true
                      source:
                        type: string
                        enum: [project, env]
                      secret:
                        type: boolean
      '400':
        description: Bad Request - No project found.
      '401':
        description: Unauthorized - only administrators may read project settings.
      '503':
        description: The encryption key of the server is not configured.
    """

    async def handle_request(request: web.Request) -> web.Response:
        match find_existing_project_dir(request):
            case web.Response() as error_response:
                return error_response
            case project_dir:
                try:
                    return settings_response(await get_settings_view(project_dir))
                except SecretCipherError as error:
                    return encryption_unavailable_response(error)

    return await handle_error(handle_request, request=request)


@routes.patch(PROJECT_SETTINGS_PATH)
async def update_project_settings(request: web.Request) -> web.Response:
    """
    Changes settings of a project
    ---
    summary: Sets or resets models and API keys of a project. Administrators only. Changes are effective immediately.
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
        required: false
        description: The engine of the project.
        schema:
          type: string
          enum: [lightrag, cag]
          default: lightrag
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - settings
            properties:
              settings:
                type: object
                description: >
                  The settings to change. A string sets the value for this project, null resets
                  the setting to the value of the server configuration (.env).
                  Settings are OPENAI_API_KEY, OPENAI_API_MODEL, OPENAI_API_MODEL_EMBEDDING,
                  AUDIO_MODEL, GEMINI_API_KEY, OPENROUTER_API_KEY, OPENROUTER_MODEL,
                  OPENROUTER_PROVIDER, TOGETHERAI_API_KEY, LIGHTRAG_MODEL, LIGHTRAG_LITE_MODEL,
                  LIGHTRAG_MODEL_TYPE (google, openai, togetherai, openrouter),
                  LIGHTRAG_REASONING_EFFORT (OpenRouter reasoning effort, e.g. minimal, none, low)
                  and CAG_MODEL.
                additionalProperties:
                  type: string
                  nullable: true
                example:
                  LIGHTRAG_MODEL: gpt-4o
                  OPENAI_API_KEY: sk-...
                  CAG_MODEL: null
    security:
      - bearerAuth: []
    responses:
      '200':
        description: The settings after the change, in the format of the GET endpoint.
      '400':
        description: Bad Request - unknown setting, invalid value or no project found.
      '401':
        description: Unauthorized - only administrators may change project settings.
      '404':
        description: The project does not exist in the database.
      '409':
        description: The embedding model of an already indexed project cannot be changed.
      '503':
        description: The encryption key of the server is not configured, so secrets cannot be stored.
    """

    async def handle_request(request: web.Request) -> web.Response:
        match find_existing_project_dir(request):
            case web.Response() as error_response:
                return error_response
            case project_dir:
                try:
                    values = parse_settings_update(request["data"]["body"])
                    await apply_settings_update(project_dir, values)
                    return settings_response(await get_settings_view(project_dir))
                except ValueError as error:
                    return invalid_response("Invalid settings", str(error))
                except ProjectNotInDatabaseError as error:
                    return invalid_response(
                        "Project not found", str(error), status=NOT_FOUND
                    )
                except EmbeddingModelLockedError as error:
                    return invalid_response(
                        "Embedding model locked", str(error), status=CONFLICT
                    )
                except SecretCipherError as error:
                    return encryption_unavailable_response(error)

    return await handle_error(handle_request, request=request)


@routes.delete(PROJECT_SETTINGS_PATH)
async def delete_project_settings(request: web.Request) -> web.Response:
    """
    Removes all settings of a project
    ---
    summary: Removes every setting of a project, so it uses the server configuration (.env) again. Administrators only.
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
        required: false
        description: The engine of the project.
        schema:
          type: string
          enum: [lightrag, cag]
          default: lightrag
    security:
      - bearerAuth: []
    responses:
      '200':
        description: The settings after the removal, in the format of the GET endpoint.
      '400':
        description: Bad Request - No project found.
      '401':
        description: Unauthorized - only administrators may change project settings.
      '404':
        description: The project does not exist in the database.
      '409':
        description: The project is indexed with an embedding model which differs from the server configuration, so the settings cannot be removed.
      '503':
        description: The encryption key of the server is not configured, so the stored settings cannot be read.
    """

    async def handle_request(request: web.Request) -> web.Response:
        match find_existing_project_dir(request):
            case web.Response() as error_response:
                return error_response
            case project_dir:
                try:
                    await clear_project_settings(project_dir)
                    return settings_response(await get_settings_view(project_dir))
                except ProjectNotInDatabaseError as error:
                    return invalid_response(
                        "Project not found", str(error), status=NOT_FOUND
                    )
                except EmbeddingModelLockedError as error:
                    return invalid_response(
                        "Embedding model locked", str(error), status=CONFLICT
                    )
                except SecretCipherError as error:
                    return encryption_unavailable_response(error)

    return await handle_error(handle_request, request=request)

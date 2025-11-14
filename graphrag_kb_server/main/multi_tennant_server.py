from datetime import datetime, timezone

from aiohttp import web

from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.model.admin import AdminUser
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.service.db.db_persistence_admin_user import delete_admin_user, insert_admin_user, select_admin_user, select_all_admin_users
from graphrag_kb_server.service.jwt_service import generate_token, decode_token
from graphrag_kb_server.service.login import admin_login
from graphrag_kb_server.service.tennant import (
    delete_tennant_folder_by_folder,
    list_tennants as local_list_tennants,
)
from graphrag_kb_server.service.validations import validate_email, validate_password
from graphrag_kb_server.model.snippet import Snippet, Project
from graphrag_kb_server.service.snippet_generation_service import (
    generate_snippet,
    inject_scripts_path,
)
from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import admin_cfg, jwt_cfg, cfg
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.service.generate_url_service import generate_direct_url


UNAUTHORIZED = 401

TENNANT_CREATE_PATH = "/protected/tennant/create"
TENNANT_DELETE_PATH = "/protected/tennant/delete_tennant"

ADMIN_TOKEN_PATH = "/tennant/admin_token"
ADMIN_CREATE_PATH = "/admin/create"
ADMIN_DELETE_PATH = "/admin/delete"
ADMIN_LIST_PATH = "/admin/list"

TOKEN_DATA = "token_data"


routes = web.RouteTableDef()


async def _validate_token(token: str) -> dict:
    try:
        token_dict = await decode_token(token)
        return token_dict
    except Exception:
        logger.error("Cannot decode token")
        raise web.HTTPUnauthorized(reason="Invalid JWT token", headers=CORS_HEADERS)


async def authenticate_request(request) -> dict:
    auth_header = request.headers.get("Authorization", None)
    if request.method == "OPTIONS" or request.path == ADMIN_TOKEN_PATH:
        # Options should be not authenticated.
        return {}
    if not auth_header or not auth_header.startswith("Bearer "):
        token = request.rel_url.query.get(
            "token", None
        )  # You can also pass the token in the query string
        if not token:
            raise web.HTTPUnauthorized(
                reason="Missing or invalid Authorization header", headers=CORS_HEADERS
            )
        else:
            return await _validate_token(token)
    token = auth_header[len("Bearer ") :]
    return await _validate_token(token)


@web.middleware
async def auth_middleware(request: web.Request, handler):

    request_path = str(request.path)
    # Check if the request path is unprotected
    if not request_path.startswith("/protected") or request_path == ADMIN_TOKEN_PATH:
        return await handler(request)

    # Authenticate for protected routes
    try:
        token_dict = await authenticate_request(request)
        request[TOKEN_DATA] = token_dict

        # All tennant routes are only accessible to administrators
        if request_path.startswith("/protected/tennant"):
            email = token_dict["email"]
            if email not in admin_cfg.administrators:
                return web.json_response(
                    {"error": "Only administrators can create or delete tennants."},
                    status=UNAUTHORIZED,
                    headers=CORS_HEADERS,
                )

        permissions = token_dict.get("permissions", ["read", "write"])
        allowed_post_paths = [
            "/protected/project/chat",
            "/protected/search",
            "/protected/project/questions",
            "/protected/project/related_topics",
            "/protected/pdf/generate",
        ]
        if (
            request.method in ["POST", "PATCH", "DELETE"]
            and "write" not in permissions
            and not any([request_path.startswith(path) for path in allowed_post_paths])
        ):
            return web.json_response(
                {
                    "error": "Only subjects with write permissions can perform this action."
                },
                status=UNAUTHORIZED,
                headers=CORS_HEADERS,
            )
    except web.HTTPUnauthorized as e:
        logger.error(f"Unauthorized access attempt: {e.reason}")
        return web.json_response(
            {"error": e.reason}, status=UNAUTHORIZED, headers=CORS_HEADERS
        )

    # If authenticated, proceed to the next handler
    return await handler(request)


@routes.options(ADMIN_TOKEN_PATH)
async def read_admin_token(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get(ADMIN_TOKEN_PATH)
async def read_admin_token(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: reads the admin token from the environment variables if the requester knows the name and email used to generate it.
    tags:
      - admin
    security: []  # Empty security array indicates no authentication required
    parameters:
      - name: name
        in: query
        required: true
        description: The name used to generate the admin token
        schema:
          type: string
      - name: email
        in: query
        required: true
        description: The email used to generate the admin token
        schema:
          type: string
      - name: password
        in: query
        required: true
        description: The password used to generate the admin token
        schema:
          type: string
    responses:
      '200':
        description: Returns the admin token if the name and email are correct.
        content:
          application/json:
            schema:
              type: object
              required:
                - token
              properties:
                token:
                  type: string
                  description: The generated JWT token
      '401':
        description: Expected response when the user name and email do not match the ones used to generate the admin token.
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - description
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
    """
    query = request.rel_url.query
    name = query.get("name", "")
    email = query.get("email", "")
    password = query.get("password", "")
    if (
        (admin_user := await admin_login(name, email, password)) is not None
    ):
        return web.json_response({"token": admin_user.jwt_token}, headers=CORS_HEADERS)
    else:
        return invalid_response(
            "Invalid name or email",
            "Make sure you specify the email and name used to generate the token.",
            status=401,
        )


@routes.options(ADMIN_CREATE_PATH)
async def create_admin_user_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post(ADMIN_CREATE_PATH)
async def create_admin_user(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: creates a new admin user
    tags:
      - admin
    security:
      - bearerAuth: []
    parameters:
      - name: name
        in: query
        required: true
        description: The name used to generate the admin token
        schema:
          type: string
      - name: email
        in: query
        required: true
        description: The email used to generate the admin token
        schema:
          type: string
      - name: password
        in: query
        required: true
        description: The password used to generate the admin token
        schema:
          type: string
    responses:
      '200':
        description: Returns the created admin user with corresponding token.
        content:
          application/json:
            schema:
              type: object
              required:
                - token
                - email
                - name
              properties:
                token:
                  type: string
                  description: The generated token
                email:
                  type: string
                  description: The email of the admin user
      '409':
        description: Expected response when the admin user already exists.
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - description
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
    """
    async def handle_request(request: web.Request) -> web.Response:
        query = request.rel_url.query
        name = query.get("name", "")
        email = query.get("email", "")
        password = query.get("password", "")
        if not validate_email(email):
            return invalid_response(
                "Invalid email", "Make sure you specify a valid email", status=400
            )
        if not validate_password(password):
            return invalid_response(
                "Invalid password", "Make sure you specify a valid password", status=400
            )
        if await select_admin_user(email) is not None:
            return invalid_response(
                "Admin user already exists",
                "The admin user already exists.",
                status=409
            )
        else:
            admin_user = AdminUser(
                name=name,
                email=email,
                password_plain=password,
            )
            await insert_admin_user(admin_user)
            return web.json_response({
              "token": jwt_cfg.admin_jwt,
              "email": email,
              "name": name,
            }, headers=CORS_HEADERS)
    return await handle_error(handle_request, request=request, headers=CORS_HEADERS)


@routes.options(ADMIN_DELETE_PATH)
async def delete_admin_user_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.delete(ADMIN_DELETE_PATH)
async def delete_admin_user_options(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: deletes an admin user
    tags:
      - admin
    security:
      - bearerAuth: []
    parameters:
      - name: email
        in: query
        required: true
        description: The email used to generate the admin token
        schema:
          type: string
    responses:
      '200':
        description: Confirms the deletion of the admin user.
        content:
          application/json:
            schema:
              type: object
              required:
                - deleted
              properties:
                deleted:
                  type: boolean
                  description: True if the admin user was deleted, False otherwise
    """
    async def handle_request(request: web.Request) -> web.Response:
        query = request.rel_url.query
        email = query.get("email", "")
        deleted =await delete_admin_user(email)
        return web.json_response({"deleted": deleted}, headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request, headers=CORS_HEADERS)


@routes.options(ADMIN_LIST_PATH)
async def admin_list_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get(ADMIN_LIST_PATH)
async def admin_list(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: Lists all admin users
    tags:
      - admin
    security:
      - bearerAuth: []
    responses:
      '200':
        description: List the admin users
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                required:
                  - username
                  - email
                properties:
                  username:
                    type: string
                    description: The username of the admin user
                  email:
                    type: string
                    description: The email of the admin user
    """
    async def handle_request(_: web.Request) -> web.Response:
        admin_users = await select_all_admin_users()
        return web.json_response(admin_users, headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request, headers=CORS_HEADERS)


@routes.options(TENNANT_CREATE_PATH)
async def create_tennant_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post(TENNANT_CREATE_PATH)
async def create_tennant(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: creates a tennant and returns a JSON token which can be used to operate in the context of the tennant.
    tags:
      - admin
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - email
              - tennant_name
            properties:
              email:
                type: string
                description: The email
              tennant_name:
                type: string
                description: The name of the tennant
    responses:
      '200':
        description: Expected response to a valid request
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - token
                - folder_name
              properties:
                email:
                  type: string
                  description: The email
                token:
                  type: string
                  description: The generated token
                folder_name:
                  type: string
                  description: The name of the folder with all of the GraphRAG files
      '400':
        description: Expected response when the folder already exists or the tennant cannot be created.
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - folder_name
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
      '401':
        description: Unauthorized
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "email" in body and "tennant_name" in body:
            email = body["email"]
            if not validate_email(email):
                return invalid_response(
                    "Invalid email", "Make sure you specify a valid email"
                )
            token_data = JWTTokenData(name=body["tennant_name"], email=email)
            jwt_token: JWTToken | Error = await generate_token(token_data)
            if isinstance(jwt_token, JWTToken):
                return web.json_response(jwt_token.model_dump(), headers=CORS_HEADERS)
            else:
                return web.json_response(
                    jwt_token.model_dump(), status=400, headers=CORS_HEADERS
                )
        else:
            return invalid_response(
                "Invalid request body",
                "Make sure you specify the email and project name.",
            )

    return await handle_error(handle_request, request=request, headers=CORS_HEADERS)


@routes.options(TENNANT_DELETE_PATH)
async def delete_tennant_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.delete(TENNANT_DELETE_PATH)
async def delete_tennant(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: Deletes a single tennant
    tags:
      - admin
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - tennant_folder
            properties:
              tennant_folder:
                type: string
                description: The tennant folder to be deleted
    responses:
      '200':
        description: Expected response to a valid request when the folder was deleted.
        content:
          application/json:
            schema:
              type: object
              required:
                - message
              properties:
                message:
                  type: string
                  description: The email
      '400':
        description: Expected response when the folder could not be deleted or does not exist.
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - folder_name
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
      '401':
        description: Unauthorized
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "tennant_folder" not in body:
            return invalid_response(
                "Tennant name is missing", "Make sure you specify a valid tennant."
            )
        tennant_folder = body["tennant_folder"]
        response = await delete_tennant_folder_by_folder(tennant_folder)
        if not response:
            return invalid_response(
                "No tennant folder.",
                "Tennant folder does not exist.",
                ErrorCode.TENNANT_DOES_NOT_EXIST,
            )
        return web.json_response({"message": "Tennant deleted"}, headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request, headers=CORS_HEADERS)


@routes.options("/protected/tennant/list_tennants")
async def list_tennants_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/tennant/list_tennants")
async def list_tennants(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: lists all available tennants in the system.
    tags:
      - admin
    security:
      - bearerAuth: []
    responses:
      '200':
        description: Returns the list of tennants
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                required:
                  - folder_name
                  - creation_timestamp
                properties:
                  folder_name:
                    type: string
                    description: The name of the folder in which the tennant's projects are located.
                  creation_timestamp:
                    type: string
                    format: date-time
                    description: The timestamp indicating when the tennant was created.
      '401':
        description: Unauthorized. The client must provide a valid Bearer token.
      '500':
        description: Internal server error.
    """

    async def handle_request(_: web.Request) -> web.Response:
        tennants = local_list_tennants()
        return web.json_response([t.as_dict() for t in tennants], headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request)


@routes.post("/protected/token/create_read_only_token")
async def create_read_only_token(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: used to create a read only token for accessing a tennancy
    tags:
      - tennant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - email
            properties:
              email:
                type: string
                description: The email
    responses:
      '200':
        description: Expected response to a valid request
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - token
                - folder_name
              properties:
                email:
                  type: string
                  description: The email
                token:
                  type: string
                  description: The generated token
      '400':
        description: Expected response when the data is invalid
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - folder_name
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
      '401':
        description: Unauthorized
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "email" in body:
            email = body["email"]
            sub = request[TOKEN_DATA]["sub"]
            jwt_token: JWTToken | Error = await _generate_jwt_token(email, sub)
            if isinstance(jwt_token, JWTToken):
                return web.json_response(jwt_token.model_dump())
            else:
                return web.json_response(jwt_token.model_dump(), status=400)
        else:
            return invalid_response(
                "Invalid request body",
                "Make sure you specify the email and project name.",
            )

    return await handle_error(handle_request, request=request)


async def _generate_jwt_token(email: str, sub: str) -> JWTToken | Error:
    token_data = JWTTokenData(name=sub, email=email)
    jwt_token: JWTToken | Error = await generate_token(
        token_data, generate_folder=False, read_only=True
    )
    return jwt_token


async def _generate_jwt_token_from_email(
    body: dict, request: web.Request
) -> str | web.Response:
    # Generate a new JWT token
    email = body["email"]
    sub = request["token_data"][
        "sub"
    ]  # Comes from the authentication token handled by the auth_middleware
    jwt_token: JWTToken | Error = await _generate_jwt_token(email, sub)
    if isinstance(jwt_token, JWTToken):
        return jwt_token.token
    else:
        return invalid_response(
            "Failed to generate JWT token",
            "Failed to generate JWT token",
            headers=CORS_HEADERS,
        )


@routes.options("/protected/snippet/generate_snippet")
async def create_snippet_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/snippet/generate_snippet")
async def create_snippet(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: used to create a snippet for a chat experience.
    tags:
      - tennant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              email:
                type: string
                description: The email
                default: "john.doe@graphrag.com"
              widget_type:
                type: string
                description: The type of widget to be used
                default: "FLOATING_CHAT"
                enum:
                  - FLOATING_CHAT
                  - CHAT
              root_element_id:
                type: string
                description: The id of the root element to be used
                default: "root"
              jwt:
                type: string
                description: The JWT token. If not provided, the snippet will be generated for the project in the request body.
              organisation_name:
                type: string
                description: The name of the organisation
                default: "My Organisation"
              streaming:
                type: string
                description: The streaming. One of true of false.
                default: "false"
              project:
                type: object
                properties:
                  name:
                    type: string
                    description: The name of the project
                  search_type:
                    type: string
                    description: The type of search to be used
                    enum:
                      - local
                      - global
                      - all
                  platform:
                    type: string
                    description: The platform to be used
                    enum:
                      - lightrag
                      - graphrag
                  additional_prompt_instructions:
                    type: string
                    description: The additional prompt instructions
                    default: "You are a helpful assistant."
                required:
                  - name
                  - search_type
                  - platform
                  - additional_prompt_instructions
            required:
              - email
              - widget_type
              - root_element_id
    responses:
      '200':
        description: Expected response to a valid request
        content:
          application/json:
            schema:
              type: object
              properties:
                snippet:
                  type: string
                  description: The snippet code
      '400':
        description: Expected response when the data is invalid
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - folder_name
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
      '401':
        description: Unauthorized
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "email" in body and "widget_type" in body and "root_element_id" in body:
            jwt_token = body.get("jwt", None)
            if jwt_token is None or jwt_token.strip() == "":
                # Generate a new JWT token
                jwt_token = await _generate_jwt_token_from_email(body, request)
                if isinstance(jwt_token, web.Response):
                    #
                    return jwt_token
            timestamp = (
                datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            snippet = Snippet(
                widget_type=body["widget_type"],
                root_element_id=body["root_element_id"],
                jwt=jwt_token,
                project=Project(
                    **body["project"], updated_timestamp=timestamp, input_files=[]
                ),
                css_path="",
                script_path="",
                base_server=cfg.server_base_url,
                websocket_server=cfg.server_base_url.replace("http", "ws"),
                organisation_name=body.get("organisation_name", ""),
                streaming=body.get("streaming", ""),
            )
            inject_scripts_path(snippet)
            generated_snippet = generate_snippet(snippet)
            return web.json_response(
                {"snippet": generated_snippet}, headers=CORS_HEADERS
            )
        else:
            return invalid_response(
                "Invalid request body",
                "Make sure you specify the email, widget type, and root element id.",
                headers=CORS_HEADERS,
            )

    return await handle_error(handle_request, request=request)


@routes.options("/protected/url/generate_direct_url")
async def generate_direct_url_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/url/generate_direct_url")
async def generate_direct_url_post(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: used to create a snippet for a chat experience.
    tags:
      - tennant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              chat_type:
                type: string
                description: The type of chat to be used
                enum:
                  - FLOATING_CHAT
                  - CHAT
              email:
                type: string
                description: The email
                default: "john.doe@graphrag.com"
              streaming:
                type: string
                description: The streaming. One of true of false.
                default: "false"
              project:
                type: object
                properties:
                  name:
                    type: string
                    description: The name of the project
                  search_type:
                    type: string
                    description: The type of search to be used
                    enum:
                      - local
                      - global
                      - all
                  platform:
                    type: string
                    description: The platform to be used
                    enum:
                      - lightrag
                      - graphrag
                      - cag
                  additional_prompt_instructions:
                    type: string
                    description: The additional prompt instructions
                    default: "You are a helpful assistant."
                required:
                  - name
                  - search_type
                  - platform
                  - additional_prompt_instructions
            required:
              - chat_type
              - project
    responses:
      '200':
        description: Expected response to a valid request
        content:
          application/json:
            schema:
              type: object
              properties:
                url:
                  type: string
                  description: The URL to be used
      '400':
        description: Expected response when the data is invalid
        content:
          application/json:
            schema:
              type: object
              required:
                - error_code
                - error
                - folder_name
              properties:
                error_code:
                  type: integer
                  description: The error code
                error:
                  type: string
                  description: The error name
                description:
                  type: string
                  description: The description of the error
      '401':
        description: Unauthorized
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "chat_type" in body and "project" in body:
            chat_type = body["chat_type"]
            streaming = body.get("streaming", "false")
            project = {
                **body["project"],
                "updated_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            jwt_token = await _generate_jwt_token_from_email(body, request)
            if isinstance(jwt_token, web.Response):
                # If the JWT token is invalid, return the error response
                return jwt_token
            url = generate_direct_url(
                chat_type, Project(**project), jwt_token, streaming == "true"
            )
            return web.json_response({"url": url}, headers=CORS_HEADERS)
        else:
            return invalid_response(
                "Invalid request body",
                "Make sure you specify the chat type and project.",
            )

    return await handle_error(handle_request, request=request)


@routes.options("/token/validate_token")
async def validate_token_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/token/validate_token")
async def validate_token(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: used to validate a token for accessing a tennancy. This is a public endpoint and can be used to validate a token without authentication.
    tags:
      - tennant
    security: []  # Empty security array indicates no authentication required
    parameters:
      - name: token
        in: query
        required: true
        description: The token to be validated
        schema:
          type: string
    responses:
      '200':
        description: If the token is valid and the token is a read write token
        content:
          application/json:
            schema:
              type: object
              properties:
                snippet:
                  type: string
                  description: The snippet code
      '401':
        description: Unauthorized in case the token is invalid or the token is a read only token
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  description: The error message
    """

    async def handle_request(request: web.Request) -> web.Response:
        token = request.rel_url.query.get("token", None)
        if token is None or token.strip() == "":
            return invalid_response(
                "Invalid token", "Please specify a valid token", headers=CORS_HEADERS
            )
        token_dict = await _validate_token(token)

        if token_dict.get("permissions", ["read", "write"]) == ["read", "write"]:
            return web.json_response(
                {"message": "Token is valid", **token_dict}, headers=CORS_HEADERS
            )
        else:
            return invalid_response(
                "Invalid token",
                "Please specify a valid token",
                status=401,
                headers=CORS_HEADERS,
            )

    return await handle_error(handle_request, request=request)

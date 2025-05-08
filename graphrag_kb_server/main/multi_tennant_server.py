from aiohttp import web

from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.service.jwt_service import generate_token, decode_token
from graphrag_kb_server.service.tennant import (
    delete_tennant_folder_by_folder,
    list_tennants as local_list_tennants,
)
from graphrag_kb_server.service.validations import validate_email
from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import admin_cfg, jwt_cfg


UNAUTHORIZED = 401

ADMIN_TOKEN_PATH = "/tennant/admin_token"


routes = web.RouteTableDef()


async def authenticate_request(request) -> dict:
    auth_header = request.headers.get("Authorization", None)
    if request.method == "OPTIONS" or request.path == ADMIN_TOKEN_PATH:
        # Options should be not authenticated.
        return {}
    if not auth_header or not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Missing or invalid Authorization header")
    token = auth_header[len("Bearer ") :]
    try:
        token_dict = await decode_token(token)
        return token_dict
    except Exception:
        logger.error("Cannot decode token")
        raise web.HTTPUnauthorized(reason="Invalid JWT token")


@web.middleware
async def auth_middleware(request: web.Request, handler):

    request_path = str(request.path)
    # Check if the request path is unprotected
    if not request_path.startswith("/protected") or request_path == ADMIN_TOKEN_PATH:
        return await handler(request)

    # Authenticate for protected routes
    try:
        token_dict = await authenticate_request(request)
        request["token_data"] = token_dict

        # All tennant routes are only accessible to administrators
        if request_path.startswith("/protected/tennant"):
            email = token_dict["email"]
            if email not in admin_cfg.administrators:
                return web.json_response(
                    {"error": "Only administrators can create or delete tennants."},
                    status=UNAUTHORIZED,
                )
    except web.HTTPUnauthorized as e:
        logger.error(f"Unauthorized access attempt: {e.reason}")
        return web.json_response({"error": e.reason}, status=UNAUTHORIZED)

    # If authenticated, proceed to the next handler
    return await handler(request)


@routes.get(ADMIN_TOKEN_PATH)
async def read_admin_token(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: reads the admin token from the environment variables if the requester knows the name and email used to generate it.
    tags:
      - tennant
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
    if name == jwt_cfg.admin_token_name and email == jwt_cfg.admin_token_email:
        return web.json_response({"token": jwt_cfg.admin_jwt})
    else:
        return invalid_response(
            "Invalid name or email",
            "Make sure you specify the email and name used to generate the token.",
            status=401,
        )


@routes.post("/protected/tennant/create")
async def create_tennant(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: creates a tennant and returns a JSON token which can be used to operate in the context of the tennant.
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
                return web.json_response(jwt_token.model_dump())
            else:
                return web.json_response(jwt_token.model_dump(), status=400)
        else:
            return invalid_response(
                "Invalid request body",
                "Make sure you specify the email and project name.",
            )

    return await handle_error(handle_request, request=request)


@routes.delete("/protected/tennant/delete_tennant")
async def delete_tennant(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: Deletes a single tennant
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
        response = delete_tennant_folder_by_folder(tennant_folder)
        if not response:
            return invalid_response(
                "No tennant folder.",
                "Tennant folder does not exist.",
                ErrorCode.TENNANT_DOES_NOT_EXIST,
            )
        return web.json_response({"message": "Tennant deleted"})

    return await handle_error(handle_request, request=request)


@routes.get("/protected/tennant/list_tennants")
async def list_tennants(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: lists all available tennants in the system.
    tags:
      - tennant
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

    async def handle_request(request: web.Request) -> web.Response:
        tennants = local_list_tennants()
        return web.json_response([t.as_dict() for t in tennants])

    return await handle_error(handle_request, request=request)


logger.info("multi_tennant_server.py loaded")

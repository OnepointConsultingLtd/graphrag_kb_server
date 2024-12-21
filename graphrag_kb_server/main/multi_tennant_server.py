from aiohttp import web
from aiohttp.web import Response

from graphrag_kb_server.main.error_handler import handle_error
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.service.jwt_service import generate_token, decode_token
from graphrag_kb_server.service.tennant import delete_tennant_folder_by_folder
from graphrag_kb_server.service.validations import validate_email
from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import admin_cfg


UNAUTHORIZED = 401


routes = web.RouteTableDef()


async def authenticate_request(request) -> dict:
    auth_header = request.headers.get("Authorization", None)
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
async def auth_middleware(request, handler):

    request_path = str(request.path)
    # Check if the request path is unprotected
    if not request_path.startswith("/protected"):
        return await handler(request)

    # Authenticate for protected routes
    try:
        token_dict = await authenticate_request(request)

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


def invalid_response(
    error_name: str,
    error_description: str,
    error_code: ErrorCode = ErrorCode.INVALID_INPUT,
) -> Response:
    return web.json_response(
        Error(
            error_code=error_code,
            error=error_name,
            description=error_description,
        ).model_dump(),
        status=400,
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

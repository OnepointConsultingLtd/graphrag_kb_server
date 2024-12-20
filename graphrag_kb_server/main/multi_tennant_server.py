from aiohttp import web

from graphrag_kb_server.main.error_handler import handle_error
from graphrag_kb_server.model.jwt_token import JWTToken, JWTTokenData
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.service.jwt import generate_token


routes = web.RouteTableDef()


@routes.post("/create_tennant")
async def create_tennant(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: creates a tennant and returns a JSON token which can be used to operate in the context of the tennant.
    tags:
      - tennant
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
    """

    async def handle_request(request: web.Request) -> web.Response:
        body = await request.json()
        if "email" in body and "tennant_name" in body:
            token_data = JWTTokenData(name=body["tennant_name"], email=body["email"])
            jwt_token: JWTToken | Error = await generate_token(token_data)
            if isinstance(jwt_token, JWTToken):
                return web.json_response(jwt_token.model_dump())
            else:
                return web.json_response(jwt_token.model_dump(), status=400)
        else:
            return web.json_response(
                Error(
                    error_code=ErrorCode.INVALID_INPUT,
                    error="Invalid request body",
                    description="Make sure you specify the email and project name",
                ).model_dump(),
                status=400,
            )

    import traceback

    traceback.print_stack()
    return await handle_error(handle_request, request=request)

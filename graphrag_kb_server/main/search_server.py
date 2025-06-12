from pathlib import Path
from aiohttp import web
from aiohttp.web import Response

from graphrag_kb_server.main.error_handler import handle_error
from graphrag_kb_server.main.project_request_functions import (
    extract_tennant_folder,
    handle_project_folder,
)

#
routes = web.RouteTableDef()


@routes.post("/protected/search/match_entities")
async def match_entities(request: web.Request) -> web.Response:
    """
    Given a user profile and topics of interest, find matching the entities to the user profile and topics of interest
    ---
    summary: returns the matching entities to the user profile and topics of interest
    tags:
      - search
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
        description: The type of engine used to run the RAG system. Only LightRAG at the moment.
        schema:
          type: string
          enum: [lightrag]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_profile:
                type: string
                description: The profile of the user, describing his interests.
                default: "John Doe is an embedded systems engineer who is interested in automation and Internet of Things."
              topics_of_interest:
                type: array
                items:
                  type: object
                  properties:
                    name:
                      type: string
                      description: The name of the entity
                      default: "AI"
                    type:
                      type: string
                      description: The type of the entity
                      default: "category"
                    description:
                      type: string
                      description: The description of the entity
                      default: "Artificial Intelligence including Deep Learning, Machine Learning, and Neural Networks"
              entity_types:
                type: array
                items:
                  type: string
                  description: The type of the entity
                  default: "category"
              entities_limit:
                type: integer
                description: The number of entities to return
                default: 10
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
                        pass

    return await handle_error(handle_request, request=request)

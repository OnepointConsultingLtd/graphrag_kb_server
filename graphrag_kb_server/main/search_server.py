from typing import Callable

from pathlib import Path
from aiohttp import web
from aiohttp.web import Response

from graphrag_kb_server.main.error_handler import handle_error
from graphrag_kb_server.main.project_request_functions import (
    extract_tennant_folder,
    handle_project_folder,
)
from graphrag_kb_server.model.search.match_query import MatchQuery
from graphrag_kb_server.service.search.matching import (
    match_entities_with_lightrag,
)
from graphrag_kb_server.service.search.search_documents import (
    retrieve_relevant_documents,
)
from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
)
from graphrag_kb_server.main.cors import CORS_HEADERS

#
routes = web.RouteTableDef()


async def _handle_request(request: web.Request, func: Callable) -> web.Response:
    match extract_tennant_folder(request):
        case Response() as error_response:
            return error_response
        case Path() as tennant_folder:
            match handle_project_folder(request, tennant_folder):
                case Response() as error_response:
                    return error_response
                case Path() as project_dir:
                    body = request["data"]["body"]

                    async def func_wrapper(_: web.Request):
                        return await func(project_dir, body)

                    return func_wrapper


@routes.options("/protected/search/expand_entities")
async def match_entities_options(request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/search/expand_entities")
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
              question:
                type: string
                description: The question used to find extra entities. This is optional.
                nullable: true
                default: "How can I use AI to improve my automation and achieve truly autonomous systems?"
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
                default: 50
              score_threshold:
                type: number
                description: The score threshold for the entities
                default: 0.5
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

    async def handle_expansion(project_dir: Path, body: dict) -> web.Response:
        match_query = MatchQuery(**body)
        match_output = await match_entities_with_lightrag(
            project_dir, match_query, score_threshold=match_query.score_threshold
        )
        return web.json_response(match_output.model_dump(), headers=CORS_HEADERS)

    return await handle_error(
        await _handle_request(request, handle_expansion), request=request
    )


@routes.post("/protected/search/relevant_documents")
async def relevant_documents(request: web.Request) -> web.Response:
    """
    Given a user profile an optional question and expanded topics of interest, find matching documents and explain their relevance to the user's interests and question.
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
              question:
                type: string
                description: The question used to find documents. This is optional.
                nullable: true
                default: "How can I use AI to improve my automation and achieve truly autonomous systems?"
              topics_of_interest:
                type: object
                properties:
                  entity_dict:
                    type: object
                    description: A dictionary of entity names and their corresponding entity lists
                    additionalProperties:
                      type: object
                      description: A list of scored entities for a given category
                      properties:
                        entities:
                          type: array
                          description: A sorted list of entity names ordered by relevance according to the user interests
                          items:
                            type: object
                            properties:
                              entity:
                                type: string
                                description: The entity name
                              score:
                                type: number
                                format: float
                                description: The score of the entity according to the user interests
                              reasoning:
                                type: string
                                description: The reasoning behind the choice of this entity and why it matches the user interests
                              abstraction:
                                type: string
                                enum: [high-level, low-level]
                                description: >
                                  The abstraction of the entity. Whether it is a high-level (overarching topic)
                                  or low-level keyword (specific subtopic)
                            required:
                              - entity
                              - score
                              - reasoning
                              - abstraction
                      required:
                        - entities
                      example:
                        entities:
                          - entity: "Machine Learning"
                            score: 0.92
                            reasoning: "This topic frequently appears in user-relevant articles."
                            abstraction: "high-level"
                          - entity: "Edge AI"
                            score: 0.85
                            reasoning: "This aligns with the user's interest in embedded systems."
                            abstraction: "low-level"

    responses:
      '200':
        description: The matching documents and their relevance to the user's interests and question
      '400':
        description: Bad Request - No project found.
        content:
          application/json:
            example:
              status: "error"
              message: "No project found"
    """

    async def handle_search_documents(project_dir: Path, body: dict) -> web.Response:
        search_query = DocumentSearchQuery(**body)
        search_result = await retrieve_relevant_documents(project_dir, search_query)
        return web.json_response(search_result.model_dump(), headers=CORS_HEADERS)

    return await handle_error(
        await _handle_request(request, handle_search_documents), request=request
    )

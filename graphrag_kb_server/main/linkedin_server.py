from aiohttp import web

from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.service.linkedin.profile_service import extract_profile

routes = web.RouteTableDef()


@routes.options("/protected/linkedin/profile/{id}")
async def linkedin_profile_options(_: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.get("/protected/linkedin/profile/{id}")
async def linkedin_profile(request: web.Request) -> web.Response:
    """
    Optional route description
    ---
    summary: returns the linked in profile. Please note that this is a private API and should not be used too often.
    tags:
      - linkedin
    parameters:
      - name: id
        in: path
        required: true
        description: The linkedin profile id
        schema:
          type: string
    security:
      - bearerAuth: []
    responses:
      '200':
        description: The linkedin profile
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
        description: Bad Request - No project found or no profile found.
        content:
          application/json:
            example:
              error_code: 1
              error_name: "No tennant information"
              error_description: "No tennant information available in request"
    """

    async def handle_request(request: web.Request) -> web.Response:
        profile_id = request.match_info.get("id", None)
        if profile_id is None:
            return invalid_response(
                "No profile id",
                "Please specify a profile id.",
                status=400
            )
        profile = extract_profile(profile_id)
        if profile is None:
            return invalid_response(
                "Cannot find profile",
                "Please specify another profile id.",
                status=404
            )
        return web.Response(
            text=profile.model_dump_json(),
            headers={**CORS_HEADERS, "Content-Type": "application/json"},
        )

    return await handle_error(handle_request, request=request)

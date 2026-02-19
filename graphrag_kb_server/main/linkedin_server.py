from pathlib import Path
from aiohttp import web
import json

from aiohttp.web import Response

from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.service.linkedin.brightdata_service import (
    scrape_linkedin_profile,
)
from graphrag_kb_server.main.project_server import match_process_dir

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
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
      - name: source
        in: query
        required: true
        description: The source of the profile
        schema:
          type: string
          enum:
            - brightdata
            - web_scraping
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
        match match_process_dir(request):
            case Response() as error_response:
                return error_response
            case Path() as project_dir:
                profile_id = request.match_info.get("id", None)
                if profile_id is None:
                    return invalid_response(
                        "No profile id",
                        "Please specify a profile id.",
                        status=400,
                    )
                source = request.query.get("source", "brightdata")
                profile_json: str = ""
                match source:
                    case "brightdata":
                        profile = await scrape_linkedin_profile(profile_id)
                        if profile is None:
                            return invalid_response(
                                "Cannot find profile",
                                "Please specify another profile id.",
                                status=404,
                            )
                        profile_json = json.dumps(profile)
                    case "web_scraping":
                        from graphrag_kb_server.service.linkedin.apify_service import (
                            apify_extract_profile,
                        )

                        profile = await apify_extract_profile(
                            profile_id,
                            project_dir=project_dir,
                            callback=None,
                        )
                        if profile is None:
                            return invalid_response(
                                "Cannot find profile",
                                "Please specify another profile id.",
                                status=404,
                            )
                        profile_json = profile.model_dump_json()
                    case _:
                        return invalid_response(
                            "Invalid source",
                            "Please specify a valid source.",
                            status=400,
                        )

                return web.Response(
                    text=profile_json,
                    headers={**CORS_HEADERS, "Content-Type": "application/json"},
                )

    return await handle_error(handle_request, request=request)

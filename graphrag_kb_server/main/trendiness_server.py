from urllib.parse import urlparse

import aiohttp
from aiohttp import web
from graphrag_kb_server.main.cors import CORS_HEADERS
from graphrag_kb_server.main.error_handler import handle_error, invalid_response
from graphrag_kb_server.model.websocket_commands import Command
from graphrag_kb_server.service.trendiness_research import document_trendiness_processor_task
from graphrag_kb_server.utils.web_tools import fetch_and_extract_text

routes = web.RouteTableDef()

DEFAULT_EXPIRY_DAYS = 30


def _extract_bearer_token(request: web.Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :]
    token = request.rel_url.query.get("token")
    if token:
        return token
    raise web.HTTPUnauthorized(
        reason="Missing or invalid Authorization header", headers=CORS_HEADERS
    )


def _is_valid_uri(value: str) -> bool:
    parsed = urlparse(value)
    if not parsed.scheme:
        return False
    return bool(parsed.netloc or parsed.path)


def _is_http_uri(value: str) -> bool:
    return urlparse(value).scheme.lower() in ("http", "https")


def _coerce_expiry_days(value: object) -> int:
    if isinstance(value, bool):
        return DEFAULT_EXPIRY_DAYS
    try:
        return max(0, int(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_EXPIRY_DAYS


@routes.options("/protected/trendiness/document")
async def document_trendiness_options(_request: web.Request) -> web.Response:
    return web.json_response({"message": "Accept all hosts"}, headers=CORS_HEADERS)


@routes.post("/protected/trendiness/document")
async def document_trendiness(request: web.Request) -> web.Response:
    """
    Assess document trendiness from inline text and a URI document identifier
    ---
    summary: Assess how trendy a document's topics are using web search
    tags:
      - trendiness
    security:
      - bearerAuth: []
    parameters:
      - name: project
        in: query
        required: true
        description: The project name
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - document_identifier
            properties:
              text:
                type: string
                description: >
                  A summary or large extract of the document. Optional when
                  document_identifier is an http or https URL; in that case the
                  page content is fetched and extracted automatically.
              document_identifier:
                type: string
                description: >
                  A valid URI that uniquely identifies the document. When this
                  is an http or https URL and text is omitted, the page is
                  fetched to obtain the content.
                example: "https://example.com/docs/article-1"
              expiry_period_in_days:
                type: integer
                description: Number of days before a cached trend result expires
                default: 30
    responses:
      "200":
        description: Trend assessment result
        content:
          application/json:
            schema:
              type: object
              properties:
                main_topics:
                  type: array
                  items:
                    type: string
                trend_class:
                  type: string
                  enum: [HOT, RISING, STABLE, DECLINING, UNKNOWN]
                confidence:
                  type: number
                reasoning:
                  type: string
                recent_findings:
                  type: string
                visited_urls:
                  type: array
                  items:
                    type: string
                document_path:
                  type: string
      "400":
        description: Bad Request - invalid input
      "401":
        description: Unauthorized - missing or invalid bearer token
      "500":
        description: Internal server error during trend assessment
    """

    async def handle_request(request: web.Request) -> web.Response:
        project = request.rel_url.query.get("project")
        if not project:
            return invalid_response(
                "No project",
                "Please specify the project name",
            )

        body = request["data"]["body"]

        document_identifier = body.get("document_identifier")
        if not document_identifier or not isinstance(document_identifier, str):
            return invalid_response(
                "Invalid document_identifier",
                "Please provide a document_identifier field",
            )
        if not _is_valid_uri(document_identifier):
            return invalid_response(
                "Invalid document_identifier",
                "document_identifier must be a valid URI with a scheme",
            )

        text = body.get("text")

        def no_text(text: str | None) -> bool:
            return not text or not isinstance(text, str) or not text.strip()
        
        if no_text(text):
            if _is_http_uri(document_identifier):
                try:
                    text = await fetch_and_extract_text(document_identifier)
                except (aiohttp.ClientError, TimeoutError) as exc:
                    return invalid_response(
                        "Could not fetch document",
                        f"Could not fetch content from document_identifier: {exc}",
                    )
            if no_text(text):
                return invalid_response(
                    "Invalid text",
                    "Please provide a non-empty text field, or an http(s) document_identifier that can be fetched",
                )

        expiry_period_in_days = _coerce_expiry_days(
            body.get("expiry_period_in_days", DEFAULT_EXPIRY_DAYS)
        )
        token = _extract_bearer_token(request)

        collected: dict = {}

        async def send_message(
            command: Command, message: str | dict, error: Exception | None = None
        ):
            if command == Command.DOCUMENT_TRENDINESS_ERROR:
                collected["error"] = {
                    "message": message,
                    "detail": str(error) if error else None,
                }
            else:
                collected["result"] = message

        await document_trendiness_processor_task(
            token,
            project,
            document_identifier,
            expiry_period_in_days,
            send_message,
            content=text,
        )

        if error := collected.get("error"):
            status = 400 if error.get("detail") and "Document not found" in error["message"] else 500
            return web.json_response(
                {"error": error["message"], "detail": error.get("detail")},
                status=status,
                headers=CORS_HEADERS,
            )

        if "result" not in collected:
            return web.json_response(
                {"error": "No trendiness result was produced"},
                status=500,
                headers=CORS_HEADERS,
            )

        return web.json_response(collected["result"], headers=CORS_HEADERS)

    return await handle_error(handle_request, request=request)

"""
MCP server that exposes /protected/project/context as an MCP tool.

Uses the MCP streamable-HTTP transport (the modern successor to SSE) served
via FastMCP on a dedicated port (MCP_PORT, default 9000), completely separate
from the main aiohttp application.

Authentication — two options, used in priority order:
  Option A (primary):  Pass  Authorization: Bearer <jwt>  as an HTTP header
                       on every request. The middleware extracts it into a
                       ContextVar that is available within that request's task.
  Option B (fallback): Call the  authenticate(token=...)  tool once per
                       session. The token is stored server-side keyed by the
                       FastMCP client_id and reused for subsequent calls.

Client configuration example (Cursor / Claude Desktop):
  {
    "mcpServers": {
      "graphrag-kb": {
        "url": "http://localhost:9000/mcp",
        "headers": { "Authorization": "Bearer <your-jwt>" }
      }
    }
  }
"""

import logging
import os
from contextvars import ContextVar
from typing import Any

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-request token (Option A)
# Set by _BearerMiddleware for each incoming HTTP request.  Because every MCP
# tool call arrives as a separate POST request, the ContextVar is refreshed
# on each call as long as the client sends the Authorization header.
# ---------------------------------------------------------------------------
_request_token: ContextVar[str | None] = ContextVar("request_token", default=None)

# ---------------------------------------------------------------------------
# Per-session token store (Option B)
# Populated by the authenticate() tool, keyed by FastMCP client_id.
# Persists for the lifetime of the process (no explicit cleanup needed for
# a development/admin tool with a small number of concurrent sessions).
# ---------------------------------------------------------------------------
_session_tokens: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class _BearerMiddleware(BaseHTTPMiddleware):
    """Extract JWT from the Authorization header and store it in a ContextVar."""

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            _request_token.set(auth[7:])
        return await call_next(request)


# ---------------------------------------------------------------------------
# MCP application
# ---------------------------------------------------------------------------

mcp = FastMCP("GraphRAG KB")


@mcp.tool()
async def authenticate(token: str, ctx: Context) -> str:
    """
    Store a JWT bearer token for this session (Option B fallback).

    Use this tool if you cannot pass an Authorization header at connection
    time. Once set, the token is reused for all subsequent get_context calls
    in this session. You can call it again at any time to rotate the token.
    """
    client_id = ctx.client_id
    if not client_id:
        raise ValueError("Unable to determine client session ID.")
    _session_tokens[client_id] = token
    logger.info("Token stored for client %s", client_id)
    return "Token stored for this session. You can now call get_context."


@mcp.tool()
async def get_context(
    project: str,
    question: str,
    ctx: Context,
    engine: str = "lightrag",
    search: str = "all",
    context_size: int | None = None,
    format: str = "json_string",
    keywords: bool = False,
) -> str:
    """
    Retrieve the RAG knowledge-base context for a project and question.

    Args:
        project:      Project name (as shown in the dashboard).
        question:     The question for which context should be retrieved.
        engine:       RAG engine to use. Default: lightrag.
        search:       Search mode — local, global, or all. Default: all.
        context_size: Maximum context size in tokens (optional).
        format:       Output format — json_string, json, or
                      json_string_with_json. Default: json_string.
        keywords:     If True, append high/low-level keywords to the context
                      (LightRAG only). Default: False.
    """
    # Resolve token: Option A takes priority over Option B
    token = _request_token.get() or _session_tokens.get(ctx.client_id or "")
    if not token:
        raise ValueError(
            "No authentication token available. "
            "Either pass 'Authorization: Bearer <token>' as an HTTP header "
            "when connecting, or call the authenticate(token=...) tool first."
        )

    base_url = os.getenv("SERVER_BASE_URL", "http://localhost:9999")
    params: dict[str, Any] = {
        "project": project,
        "question": question,
        "engine": engine,
        "search": search,
        "format": format,
        "keywords": str(keywords).lower(),
    }
    if context_size is not None:
        params["context_size"] = context_size

    logger.info(
        "get_context: project=%s search=%s engine=%s question=%r",
        project,
        search,
        engine,
        question,
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{base_url}/protected/project/context",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        ) as response:
            body = await response.text()
            if response.status != 200:
                raise ValueError(
                    f"Upstream error [{response.status}]: {body}"
                )
            return body


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "9000"))
    logger.info("Starting GraphRAG KB MCP server on %s:%s", host, port)
    app = mcp.http_app(middleware=[Middleware(_BearerMiddleware)])
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()

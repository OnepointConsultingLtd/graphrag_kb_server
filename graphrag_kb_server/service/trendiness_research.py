"""
Service for assessing document trendiness using OpenRouter's web_search server tool.

Uses the OpenRouter API to perform live web searches about a document's topics
and classifies trendiness as HOT, RISING, STABLE, DECLINING, or UNKNOWN.
"""

import json
from pathlib import Path
from typing import Awaitable, Optional, Callable

from openrouter import OpenRouter

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.document_trend_result import TrendResult, DocumentTrendResult
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path, get_project_id_from_path
from graphrag_kb_server.service.db.db_persistence_trend_result import get_document_trend_result_by_path, insert_document_trend_result
from graphrag_kb_server.service.tennant import find_project_dir
from graphrag_kb_server.utils.file_support import strip_drive
from graphrag_kb_server.model.websocket_commands import Command

SNIPPET_MAX_CHARS = 2000
REQUEST_TIMEOUT_SECONDS = 120.0

_SYSTEM_PROMPT = """You are a trend analyst with access to real-time web search.
Given a document snippet, identify the main topics and search the web to assess how trendy those topics are right now.

Respond with a JSON object (no markdown, no code blocks) containing exactly these fields:
{
  "main_topics": ["list", "of", "main", "topics"],
  "trend_class": "HOT|RISING|STABLE|DECLINING|UNKNOWN",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<concise explanation referencing your web findings>",
  "recent_findings": "<summary of the most relevant recent results you found>"
}

Trend class definitions:
- HOT: Topic is experiencing rapid growth in interest or has major recent news/events
- RISING: Topic is steadily gaining traction over recent months
- STABLE: Topic has consistent, established interest without notable change
- DECLINING: Topic is losing relevance or coverage
- UNKNOWN: Insufficient web data to classify reliably
"""


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from a model response if present."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


async def assess_document_trendiness(
    content: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> TrendResult:
    """
    Assess the trendiness of a document snippet using OpenRouter web search.

    Sends the first SNIPPET_MAX_CHARS characters of the document to the configured
    OpenRouter model with the web_search server tool enabled. The model searches
    the web and returns a structured TrendResult.

    Args:
        content: Full text of the document (will be truncated to SNIPPET_MAX_CHARS).
        model: OpenRouter model identifier. Falls back to OPENROUTER_MODEL env var.
        api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.

    Returns:
        TrendResult with trend_class, confidence, reasoning, and recent_findings.

    Raises:
        ValueError: If no API key is available.
        httpx.HTTPStatusError: If the OpenRouter API returns an error response.
        json.JSONDecodeError: If the model response cannot be parsed as JSON.
    """
    effective_api_key = api_key or cfg.openrouter_api_key
    if not effective_api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")

    effective_model = model or cfg.openrouter_model
    snippet = content[:SNIPPET_MAX_CHARS]

    client = OpenRouter(api_key=cfg.openrouter_api_key)
    response = await client.chat.send_async(
        model=effective_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Assess the trendiness of this document:\n\n{snippet}",
            },
        ],
        plugins=[{"id": "web"}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "TrendResult",
                "schema": TrendResult.model_json_schema(),
            },
        },
    )

    raw_text = response.choices[0].message.content
    json_text = _strip_code_fences(raw_text)
    result_data = json.loads(json_text)
    return TrendResult(**result_data)


async def document_trendiness_processor_task(
    token: str,
    project: str,
    document_path_str: str,
    expiry_period_in_days: int = 30,
    send_message: Callable[[Command, str | dict, Exception | None], Awaitable[None]] | None = None,
):

    try:
        logger.info(f"Document trendiness query from websocket: {document_path_str}")
        project_dir = await find_project_dir(token, project, Engine.LIGHTRAG)
        document_path = Path(strip_drive(document_path_str))
        if not document_path.exists():
            await send_message(
                Command.DOCUMENT_TRENDINESS_ERROR,
                "Document not found",
                ValueError(f"Document not found: {document_path}"),
            )
            return
        document_path_key = strip_drive(document_path.resolve().as_posix())
        project_id = await get_project_id_from_path(project_dir)
        simple_project = extract_elements_from_path(project_dir)
        existing_trend_result = await get_document_trend_result_by_path(
            simple_project.schema_name,
            document_path_key,
            simple_project.project_name,
            expiry_period_in_days=expiry_period_in_days,
        )
        if existing_trend_result is not None:
            await send_message(
                Command.DOCUMENT_TRENDINESS_END,
                existing_trend_result.model_dump(),
                None,
            )
            return
        content = document_path.read_text(encoding="utf-8")
        trend_result = await assess_document_trendiness(content)
        await insert_document_trend_result(
            simple_project.schema_name,
            DocumentTrendResult.from_trend_result(
                document_path_key, project_id, trend_result
            ),
        )
        logger.info(f"Document trendiness result: {trend_result.model_dump()}")
        await send_message(
            Command.DOCUMENT_TRENDINESS_END,
            {**trend_result.model_dump(), "document_path": document_path_key},
            None,
        )
    except Exception as e:
        await send_message(
            Command.DOCUMENT_TRENDINESS_ERROR,
            f"Failed to extract document trendiness: {e}",
            e,
        )

"""
Service for assessing document trendiness using OpenRouter's web_search server tool.

Uses the OpenRouter API to perform live web searches about a document's topics
and classifies trendiness as HOT, RISING, STABLE, DECLINING, or UNKNOWN.
"""

import json
from enum import StrEnum
from typing import Optional

from openrouter import OpenRouter
from pydantic import BaseModel, Field

from graphrag_kb_server.config import cfg

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


class TrendClass(StrEnum):
    HOT = "HOT"
    RISING = "RISING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    UNKNOWN = "UNKNOWN"


class TrendResult(BaseModel):
    main_topics: list[str] = Field(description="The main topics of the document")
    trend_class: TrendClass = Field(description="The trend class of the document")
    confidence: float = Field(description="The confidence in the trend class")
    reasoning: str = Field(description="The reasoning for the trend class")
    recent_findings: str = Field(description="The recent findings for the trend class")
    visited_urls: list[str] = Field(description="The URLs that were visited to find the information")


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
            {"role": "user", "content": f"Assess the trendiness of this document:\n\n{snippet}"},
        ],
        plugins=[{ "id": "web" }],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "TrendResult", "schema": TrendResult.model_json_schema()},
        }
    )

    raw_text = content = response.choices[0].message.content
    json_text = _strip_code_fences(raw_text)
    result_data = json.loads(json_text)
    return TrendResult(**result_data)

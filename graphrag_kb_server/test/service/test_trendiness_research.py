"""
Test script for the trendiness_research service.

Reads document content from data/results/sample1.jsonl,
runs a trendiness assessment on each document via OpenRouter web search,
and saves the results (including per-document execution times) to
data/results/sample1_results.json.
"""

import asyncio
import json
import time
from pathlib import Path

from graphrag_kb_server.service.trendiness_research import (
    TrendResult,
    assess_document_trendiness,
)

BASE_DIR = Path(__file__).parent.parent.parent.parent
SAMPLE_JSONL_PATH = BASE_DIR / "data/results/sample1.jsonl"
RESULTS_JSON_PATH = BASE_DIR / "data/results/sample1_results.json"

assert (
    SAMPLE_JSONL_PATH.exists()
), f"Sample JSONL file {SAMPLE_JSONL_PATH} does not exist"


def _load_documents(path: Path) -> list[dict]:
    """Load all JSON objects from a JSONL file, skipping blank lines."""
    documents = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                documents.append(json.loads(line))
    return documents


def _build_result_entry(
    reference_id: str,
    content: str,
    trend_result: TrendResult,
    execution_time_seconds: float,
) -> dict:
    """Build a result record combining document metadata, trend assessment, and timing."""
    return {
        "reference_id": reference_id,
        "content_snippet": content[:300],
        "main_topics": trend_result.main_topics,
        "trend_class": str(trend_result.trend_class),
        "confidence": trend_result.confidence,
        "reasoning": trend_result.reasoning,
        "recent_findings": trend_result.recent_findings,
        "execution_time_seconds": round(execution_time_seconds, 2),
        "visited_urls": trend_result.visited_urls,
    }


def _build_error_entry(
    reference_id: str,
    content: str,
    error: Exception,
    execution_time_seconds: float,
) -> dict:
    """Build an error record when trendiness assessment fails for a document."""
    return {
        "reference_id": reference_id,
        "content_snippet": content[:300],
        "error": str(error),
        "execution_time_seconds": round(execution_time_seconds, 2),
    }


async def run_trendiness_assessment() -> None:
    """Run trendiness assessment on all documents in sample1.jsonl and save results."""
    documents = _load_documents(SAMPLE_JSONL_PATH)
    print(f"Loaded {len(documents)} documents from {SAMPLE_JSONL_PATH}")

    results = []
    total_start = time.monotonic()

    for doc in documents:
        reference_id = doc.get("reference_id", "unknown")
        content = doc.get("content", "")
        print(f"\nAssessing document {reference_id} ...")

        start = time.monotonic()
        try:
            trend_result = await assess_document_trendiness(content)
            elapsed = time.monotonic() - start
            entry = _build_result_entry(reference_id, content, trend_result, elapsed)
            print(
                f"  trend_class : {trend_result.trend_class}"
                f"  confidence  : {trend_result.confidence:.2f}"
                f"  time        : {elapsed:.1f}s"
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            entry = _build_error_entry(reference_id, content, exc, elapsed)
            print(f"  ERROR after {elapsed:.1f}s: {exc}")

        results.append(entry)

    total_elapsed = time.monotonic() - total_start

    output = {
        "total_documents": len(documents),
        "total_execution_time_seconds": round(total_elapsed, 2),
        "results": results,
    }

    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(documents)} documents assessed in {total_elapsed:.1f}s.")
    print(f"Results saved to {RESULTS_JSON_PATH}")


if __name__ == "__main__":
    asyncio.run(run_trendiness_assessment())

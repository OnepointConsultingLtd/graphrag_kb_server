from pathlib import Path
from typing import AsyncIterator
import jiter

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.rag_parameters import QueryParameters, ContextFormat
from graphrag_kb_server.main.query_support import add_links_to_response
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search


async def lightrag_get_response_stream(
    project_dir: Path,
    conversation_id: str,
    query: str,
    search: str = "hybrid",
) -> tuple[AsyncIterator[str], "_ReferenceResolver"]:
    """Execute a LightRAG streaming query and return a token iterator plus a
    deferred reference resolver.

    Returns:
        A tuple of (token_iterator, reference_resolver).
        - Iterate over token_iterator to stream text tokens to the client.
        - After the iterator is exhausted, await reference_resolver.resolve()
          to get the enriched references (with links and images).
    """
    query_params = QueryParameters(
        format="json",
        search=search,
        engine="lightrag",
        context_params={
            "query": query,
            "project_dir": project_dir,
        },
        conversation_id=conversation_id,
        stream=True,
        structured_output=True,
        context_format=ContextFormat.JSON,
    )

    chat_response: ChatResponse = await lightrag_search(query_params)

    if chat_response.response_iterator is not None:
        resolver = _ReferenceResolver(project_dir)
        token_iter = _collect_and_yield(chat_response.response_iterator, resolver)
        return token_iter, resolver
    # Only streaming response is to be supported. Alert the user about that.
    raise ValueError(
        "LightRAG did not return a streaming response. "
        "Ensure stream=True is set in QueryParameters."
    )


async def _collect_and_yield(
    response_iterator: AsyncIterator, resolver: "_ReferenceResolver"
) -> AsyncIterator[str]:
    """Consume the LLM streaming iterator, yield text tokens, and collect the
    full response so references can be extracted afterwards."""
    collected = []
    async for chunk in response_iterator:
        token = chunk if isinstance(chunk, str) else getattr(chunk, "text", str(chunk))
        collected.append(token)
        yield token

    full_response = "".join(collected)
    resolver._raw_response = full_response


class _ReferenceResolver:
    """Holds the deferred reference data.  Call ``resolve()`` after the stream
    is fully consumed to get enriched references with links and images."""

    def __init__(self, project_dir: Path):
        self._project_dir = project_dir
        self._raw_response: str | None = None
        self._references: list[dict] | None = None

    async def resolve(self) -> list[dict]:
        if self._references is not None:
            return self._references

        if self._raw_response is None:
            return []

        references = _extract_references_from_response(self._raw_response)
        self._references = await _enrich_references(references, self._project_dir)
        return self._references


def _extract_references_from_response(raw_response: str) -> list[dict]:
    """Try to parse a structured JSON response to pull out references.
    Falls back to an empty list if the response is plain text."""

    try:
        parsed = jiter.from_json(raw_response.encode("utf-8"))
        if isinstance(parsed, dict):
            return parsed.get("references", [])
    except Exception:
        logger.debug("Streamed response is not JSON; no inline references to extract")
    return []


async def _enrich_references(
    references: list[dict], project_dir: Path
) -> list[dict]:
    """Take raw reference dicts, filter out KG types, deduplicate, and attach
    links + images via the existing add_links_to_response pipeline."""
    if not references:
        return []

    references = [ref for ref in references if ref.get("type") != "KG"]
    references = list({r.get("file", ""): r for r in references}.values())

    dummy_response = ChatResponse(
        response={"references": references}
    )
    enriched = await add_links_to_response(dummy_response, project_dir)
    if enriched and isinstance(enriched.response, dict):
        return enriched.response.get("references", [])
    return references

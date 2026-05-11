"""
Service for extracting and persisting representative text chunks from LightRAG projects.

Reads kv_store_text_chunks.json produced by LightRAG, selects the first chunk
(by chunk_order_index) for each unique document, and stores it in TB_DOCUMENT_CHUNKS.
These stored chunks are later used as input for document trendiness assessment.
"""

import json
from pathlib import Path

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.document_chunk import DocumentChunk
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id,
)
from graphrag_kb_server.service.db.db_persistence_document_chunks import (
    get_stored_document_paths,
    insert_document_chunk,
)
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER

_CHUNKS_FILE = "kv_store_text_chunks.json"
_UNKNOWN_SOURCE = "unknown_source"


def _load_lightrag_chunks_json(project_folder: Path) -> dict:
    """Load the raw chunks dict from LightRAG's kv_store_text_chunks.json.

    Returns an empty dict when the file does not yet exist (project not indexed).
    """
    chunks_path = project_folder / LIGHTRAG_FOLDER / _CHUNKS_FILE
    if not chunks_path.exists():
        logger.debug("Chunks file not found, skipping: %s", chunks_path)
        return {}
    return json.loads(chunks_path.read_text(encoding="utf-8"))


def _select_first_chunk_per_document(raw_chunks: dict) -> list[dict]:
    """Select the earliest chunk (lowest chunk_order_index) for each unique document.

    When file_path is 'unknown_source', falls back to full_doc_id as the document
    identifier so the UNIQUE constraint on (DOCUMENT_PATH, PROJECT_ID) is respected.

    Returns a list of dicts with keys: document_path, chunk_id, chunk_content.
    """
    best: dict[str, dict] = {}
    for chunk_key, chunk_data in raw_chunks.items():
        full_doc_id: str = chunk_data.get("full_doc_id", chunk_key)
        file_path: str = chunk_data.get("file_path", _UNKNOWN_SOURCE)
        document_path = file_path if file_path != _UNKNOWN_SOURCE else full_doc_id
        order_index: int = chunk_data.get("chunk_order_index", 0)

        existing = best.get(full_doc_id)
        if existing is None or order_index < existing["chunk_order_index"]:
            best[full_doc_id] = {
                "document_path": document_path,
                "chunk_id": chunk_key,
                "chunk_content": chunk_data.get("content", ""),
                "chunk_order_index": order_index,
            }

    return [
        {
            "document_path": v["document_path"],
            "chunk_id": v["chunk_id"],
            "chunk_content": v["chunk_content"],
        }
        for v in best.values()
    ]


async def save_document_chunks(
    project_folder: Path, insert_if_not_exists: bool = False
):
    """Extract one representative chunk per document and persist it to Postgres.

    When insert_if_not_exists is True, documents that already have a stored chunk
    are skipped rather than attempting a redundant insert.
    """
    simple_project = extract_elements_from_path(project_folder)
    project_id = await get_project_id(
        simple_project.schema_name,
        simple_project.project_name,
        simple_project.engine.value,
        create_if_not_exists=True,
    )

    raw_chunks = _load_lightrag_chunks_json(project_folder)
    if not raw_chunks:
        return

    candidates = _select_first_chunk_per_document(raw_chunks)

    if insert_if_not_exists:
        existing_paths = await get_stored_document_paths(
            simple_project.schema_name, project_id
        )
        candidates = [c for c in candidates if c["document_path"] not in existing_paths]

    for candidate in candidates:
        chunk = DocumentChunk(
            document_path=candidate["document_path"],
            chunk_content=candidate["chunk_content"],
            chunk_id=candidate["chunk_id"],
            project_id=project_id,
        )
        await insert_document_chunk(simple_project.schema_name, chunk)

    logger.info(
        "Saved %d document chunk(s) for project '%s' (schema: %s)",
        len(candidates),
        simple_project.project_name,
        simple_project.schema_name,
    )

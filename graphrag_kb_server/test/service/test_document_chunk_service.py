"""
Unit tests for document_chunk_service pure helpers.

These tests do not require a database connection.
"""

import pytest

from graphrag_kb_server.service.document_chunk_service import (
    _load_lightrag_chunks_json,
    _select_first_chunk_per_document,
)


# ---------------------------------------------------------------------------
# _load_lightrag_chunks_json
# ---------------------------------------------------------------------------


def test_load_chunks_returns_empty_when_file_missing(tmp_path):
    """Returns an empty dict when kv_store_text_chunks.json does not exist."""
    result = _load_lightrag_chunks_json(tmp_path)
    assert result == {}


def test_load_chunks_parses_valid_json(tmp_path):
    """Parses a well-formed chunks JSON file and returns its contents."""
    lightrag_dir = tmp_path / "lightrag"
    lightrag_dir.mkdir()
    chunks_data = {
        "chunk-abc": {
            "content": "Hello world",
            "chunk_order_index": 0,
            "full_doc_id": "doc-1",
            "file_path": "/input/doc.txt",
            "tokens": 10,
        }
    }
    (lightrag_dir / "kv_store_text_chunks.json").write_text(
        __import__("json").dumps(chunks_data), encoding="utf-8"
    )
    result = _load_lightrag_chunks_json(tmp_path)
    assert "chunk-abc" in result
    assert result["chunk-abc"]["content"] == "Hello world"


# ---------------------------------------------------------------------------
# _select_first_chunk_per_document
# ---------------------------------------------------------------------------


def test_select_first_chunk_picks_lowest_index():
    """When a document has multiple chunks, the one with chunk_order_index=0 is selected."""
    raw = {
        "chunk-1": {
            "content": "First chunk",
            "chunk_order_index": 0,
            "full_doc_id": "doc-A",
            "file_path": "/input/a.txt",
        },
        "chunk-2": {
            "content": "Second chunk",
            "chunk_order_index": 1,
            "full_doc_id": "doc-A",
            "file_path": "/input/a.txt",
        },
    }
    results = _select_first_chunk_per_document(raw)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "chunk-1"
    assert results[0]["chunk_content"] == "First chunk"


def test_select_first_chunk_fallback_path_for_unknown_source():
    """When file_path is 'unknown_source', full_doc_id is used as document_path."""
    raw = {
        "chunk-x": {
            "content": "Some content",
            "chunk_order_index": 0,
            "full_doc_id": "doc-Z",
            "file_path": "unknown_source",
        }
    }
    results = _select_first_chunk_per_document(raw)
    assert len(results) == 1
    assert results[0]["document_path"] == "doc-Z"


def test_select_first_chunk_uses_file_path_when_set():
    """When file_path is a real path, it is used as document_path."""
    raw = {
        "chunk-y": {
            "content": "Content",
            "chunk_order_index": 0,
            "full_doc_id": "doc-B",
            "file_path": "/input/report.txt",
        }
    }
    results = _select_first_chunk_per_document(raw)
    assert results[0]["document_path"] == "/input/report.txt"


def test_select_first_chunk_multiple_documents():
    """Three distinct documents produce three entries."""
    raw = {
        "chunk-1": {"content": "A", "chunk_order_index": 0, "full_doc_id": "doc-1", "file_path": "/a.txt"},
        "chunk-2": {"content": "B", "chunk_order_index": 0, "full_doc_id": "doc-2", "file_path": "/b.txt"},
        "chunk-3": {"content": "C", "chunk_order_index": 0, "full_doc_id": "doc-3", "file_path": "/c.txt"},
    }
    results = _select_first_chunk_per_document(raw)
    assert len(results) == 3
    paths = {r["document_path"] for r in results}
    assert paths == {"/a.txt", "/b.txt", "/c.txt"}


def test_select_first_chunk_returns_empty_for_empty_input():
    """An empty raw_chunks dict returns an empty list."""
    assert _select_first_chunk_per_document({}) == []


def test_select_first_chunk_highest_order_index_is_not_chosen():
    """Given chunks with indices 2, 1, 0 inserted in that order, index 0 is still selected."""
    raw = {
        "chunk-last": {"content": "Tail", "chunk_order_index": 2, "full_doc_id": "doc-X", "file_path": "/x.txt"},
        "chunk-mid": {"content": "Middle", "chunk_order_index": 1, "full_doc_id": "doc-X", "file_path": "/x.txt"},
        "chunk-first": {"content": "Head", "chunk_order_index": 0, "full_doc_id": "doc-X", "file_path": "/x.txt"},
    }
    results = _select_first_chunk_per_document(raw)
    assert len(results) == 1
    assert results[0]["chunk_content"] == "Head"

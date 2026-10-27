from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from graphrag_kb_server.service.lightrag.lightrag_file_removal import (
    delete_files_from_disk,
    remove_file_from_project,
    resolve_inside_folder,
)
from graphrag_kb_server.service.lightrag.lightrag_index_support import (
    adelete_file_from_index,
    find_doc_ids_by_relative_path,
    indexed_relative_path,
    find_files_to_index,
    list_indexed_file_paths,
    zip_entry_to_indexed_relative_path,
)


def make_rag(docs: list[tuple[str, str]], delete_status: str = "success") -> MagicMock:
    """Creates a fake LightRAG with the given (doc_id, file_path) documents."""
    rag = MagicMock()
    rag.doc_status.get_docs_paginated = AsyncMock(
        return_value=(
            [(doc_id, SimpleNamespace(file_path=path)) for doc_id, path in docs],
            len(docs),
        )
    )
    rag.adelete_by_doc_id = AsyncMock(
        return_value=SimpleNamespace(status=delete_status, message="msg")
    )
    return rag


def test_zip_entry_is_mapped_to_text_file():
    assert zip_entry_to_indexed_relative_path("docs/report.pdf") == "docs/report.txt"
    assert zip_entry_to_indexed_relative_path("a.txt") == "a.txt"


def test_find_files_to_index_matches_exact_relative_path(tmp_path: Path):
    all_files = [
        tmp_path / "report.txt",
        tmp_path / "annual_report.txt",
        tmp_path / "sub" / "report.txt",
    ]
    result = find_files_to_index(tmp_path, all_files, ["report.pdf", "sub/"])
    assert result == [tmp_path / "report.txt"]


@pytest.mark.asyncio
async def test_find_doc_ids_returns_all_versions():
    rag = make_rag(
        [
            ("d1", "/srv/p/input/a.txt"),
            ("d2", "/srv/p/input/b.txt"),
            ("d3", "/old/location/input/a.txt"),
        ]
    )
    assert await find_doc_ids_by_relative_path(rag, Path("/new/input"), "a.txt") == [
        "d1",
        "d3",
    ]


@pytest.mark.asyncio
async def test_find_doc_ids_reads_all_pages():
    rag = MagicMock()
    page_one = [(f"d{i}", SimpleNamespace(file_path="/other")) for i in range(200)]
    page_two = [("last", SimpleNamespace(file_path="/p/input/a.txt"))]
    rag.doc_status.get_docs_paginated = AsyncMock(side_effect=[(page_one, 201), (page_two, 201)])
    assert await find_doc_ids_by_relative_path(rag, Path("/x/input"), "a.txt") == [
        "last"
    ]


@pytest.mark.asyncio
async def test_delete_file_from_index_deletes_each_version():
    rag = make_rag([("d1", "/p/input/a.txt"), ("d2", "/p/input/a.txt")])
    assert await adelete_file_from_index(rag, Path("/x/input"), "a.txt") == 2
    assert rag.adelete_by_doc_id.await_count == 2


@pytest.mark.asyncio
async def test_delete_file_from_index_ignores_unknown_file():
    rag = make_rag([("d1", "/p/input/b.txt")])
    assert await adelete_file_from_index(rag, Path("/x/input"), "a.txt") == 0
    rag.adelete_by_doc_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_file_from_index_raises_on_failure():
    rag = make_rag([("d1", "/p/input/a.txt")], delete_status="fail")
    with pytest.raises(RuntimeError):
        await adelete_file_from_index(rag, Path("/x/input"), "a.txt")


def test_resolve_inside_folder_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        resolve_inside_folder(tmp_path, "../secret.txt")
    with pytest.raises(ValueError):
        resolve_inside_folder(tmp_path, ".")


def test_delete_files_from_disk_removes_text_and_original(tmp_path: Path):
    from graphrag_kb_server.service.file_find_service import ORIGINAL_INPUT_FOLDER
    from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER

    (tmp_path / INPUT_FOLDER).mkdir()
    (tmp_path / ORIGINAL_INPUT_FOLDER).mkdir()
    text_file = tmp_path / INPUT_FOLDER / "report.txt"
    original_file = tmp_path / ORIGINAL_INPUT_FOLDER / "report.pdf"
    other_file = tmp_path / ORIGINAL_INPUT_FOLDER / "other.pdf"
    for file in (text_file, original_file, other_file):
        file.write_text("x")
    deleted = delete_files_from_disk(tmp_path, "report.pdf")
    assert set(deleted) == {text_file.resolve(), original_file.resolve()}
    assert other_file.exists()


@pytest.mark.asyncio
async def test_remove_file_from_project_deletes_index_and_disk(tmp_path: Path):
    from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER

    (tmp_path / INPUT_FOLDER).mkdir()
    text_file = tmp_path / INPUT_FOLDER / "a.txt"
    text_file.write_text("x")
    rag = make_rag([("d1", text_file.resolve().as_posix())])
    documents, files = await remove_file_from_project(tmp_path, "a.txt", rag)
    assert documents == 1
    assert files == [text_file.resolve()]
    assert not text_file.exists()


@pytest.mark.asyncio
async def test_list_indexed_file_paths_returns_sorted_unique_relative_paths(
    tmp_path: Path,
):
    resolved = tmp_path.resolve()
    rag = make_rag(
        [
            ("d1", (resolved / "b.txt").as_posix()),
            ("d2", (resolved / "sub" / "a.txt").as_posix()),
            ("d3", (resolved / "b.txt").as_posix()),
            ("d4", (resolved.parent / "outside" / "c.txt").as_posix()),
            ("d5", "unknown_source"),
        ]
    )
    assert await list_indexed_file_paths(rag, tmp_path) == ["b.txt", "sub/a.txt"]


@pytest.mark.asyncio
async def test_list_indexed_file_paths_is_empty_without_documents(tmp_path: Path):
    assert await list_indexed_file_paths(make_rag([]), tmp_path) == []


def test_indexed_relative_path_inside_current_input_folder(tmp_path: Path):
    stored = (tmp_path.resolve() / "sub" / "a.txt").as_posix()
    assert indexed_relative_path(stored, tmp_path) == "sub/a.txt"


def test_indexed_relative_path_uses_input_marker_for_other_prefix(tmp_path: Path):
    stored = "/var/graphrag/t/lightrag/p/input/clustre/Articles and PoVs/a.txt"
    assert indexed_relative_path(stored, tmp_path) == "clustre/Articles and PoVs/a.txt"
    assert indexed_relative_path(r"C:\data\p\input\a.txt", tmp_path) == "a.txt"


def test_indexed_relative_path_is_none_without_input_folder(tmp_path: Path):
    assert indexed_relative_path("unknown_source", tmp_path) is None


@pytest.mark.asyncio
async def test_remove_file_keeps_disk_files_when_not_indexed(tmp_path: Path):
    from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER

    (tmp_path / INPUT_FOLDER).mkdir()
    text_file = tmp_path / INPUT_FOLDER / "a.txt"
    text_file.write_text("x")
    documents, files = await remove_file_from_project(tmp_path, "a.txt", make_rag([]))
    assert (documents, files) == (0, [])
    assert text_file.exists()


@pytest.mark.asyncio
async def test_remove_file_deletes_unindexed_when_requested(tmp_path: Path):
    from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER

    (tmp_path / INPUT_FOLDER).mkdir()
    text_file = tmp_path / INPUT_FOLDER / "a.txt"
    text_file.write_text("x")
    documents, files = await remove_file_from_project(
        tmp_path, "a.txt", make_rag([]), delete_unindexed=True
    )
    assert documents == 0
    assert files == [text_file.resolve()]

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.file_find_service import ORIGINAL_INPUT_FOLDER
from graphrag_kb_server.service.indexing_job_registry import IndexingJobRegistry
from graphrag_kb_server.service.lightrag import lightrag_file_indexing
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_file_indexing import (
    MAX_INDEX_FILES,
    UploadedFile,
    convert_to_text,
    indexed_file_name,
    indexed_message,
    normalize_file_stem,
    prepare_uploaded_file,
    previous_version_names,
    replace_files_in_index,
    run_indexing_job,
    submitted_message,
    validate_uploaded_files,
)

MODULE = "graphrag_kb_server.service.lightrag.lightrag_file_indexing"


def uploaded(file_name: str, text: str) -> UploadedFile:
    """Creates an uploaded file with base64 content as produced by the multipart parser."""
    return UploadedFile(file_name, base64.b64encode(text.encode("utf-8")))


def make_rag(docs: list[tuple[str, str]]) -> MagicMock:
    """Creates a fake LightRAG with the given (doc_id, file_path) documents."""
    rag = MagicMock()
    rag.doc_status.get_docs_paginated = AsyncMock(
        return_value=(
            [(doc_id, SimpleNamespace(file_path=path)) for doc_id, path in docs],
            len(docs),
        )
    )
    rag.adelete_by_doc_id = AsyncMock(
        return_value=SimpleNamespace(status="success", message="")
    )
    return rag


def fake_pdf_conversion(text: str) -> AsyncMock:
    """Fakes the LLM conversion by writing a markdown file next to the PDF."""

    async def convert(pdf_file: Path) -> Path:
        markdown_file = pdf_file.with_suffix(".md")
        markdown_file.write_text(text, encoding="utf-8")
        return markdown_file

    return AsyncMock(side_effect=convert)


@pytest.fixture
def project_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "tennant" / "lightrag" / "project"
    (folder / INPUT_FOLDER).mkdir(parents=True)
    (folder / ORIGINAL_INPUT_FOLDER).mkdir(parents=True)
    return folder


@pytest.fixture
def upload_dir(tmp_path: Path):
    folder = tmp_path / "uploads"
    with patch.object(cfg, "upload_dir", folder):
        yield folder


def read_project_status(project_folder: Path) -> str:
    return json.loads((project_folder / "project.json").read_text())["indexing_status"]


def test_normalize_file_stem_removes_folders_and_whitespace():
    assert normalize_file_stem("My  Report.pdf") == "My_Report"
    assert normalize_file_stem("sub/dir/notes.md") == "notes"
    assert normalize_file_stem("../../evil.txt") == "evil"


def test_indexed_file_name_is_text_file():
    assert indexed_file_name("My Report.pdf") == "My_Report.txt"


def test_previous_version_names_contains_original_and_normalized_name():
    assert previous_version_names("My Report.pdf") == ["My Report.txt", "My_Report.txt"]
    assert previous_version_names("report.md") == ["report.txt"]


def test_messages():
    assert indexed_message(5, "p") == "5 file(s) indexed successfully in index p"
    assert submitted_message(2, "p") == "2 file(s) submitted for indexing in index p"


@pytest.mark.parametrize(
    "file_names",
    [
        ["a.txt"],
        ["a.md", "b.PDF", "c.txt"],
        [f"{i}.txt" for i in range(MAX_INDEX_FILES)],
    ],
)
def test_validate_uploaded_files_accepts_valid_files(file_names):
    assert validate_uploaded_files(file_names) is None


@pytest.mark.parametrize(
    "file_names, expected_error",
    [
        ([], "at least one file"),
        ([f"{i}.txt" for i in range(MAX_INDEX_FILES + 1)], "at most 5 files"),
        (["a.docx", "b.txt"], "Unsupported file type: a.docx"),
        (["noextension"], "Unsupported file type"),
        (["a b.txt", "a_b.md"], "Duplicate file names: a_b"),
        (["  .txt"], "Invalid file name"),
    ],
)
def test_validate_uploaded_files_rejects_invalid_files(file_names, expected_error):
    assert expected_error in validate_uploaded_files(file_names)


@pytest.mark.asyncio
async def test_convert_to_text_keeps_text_file(tmp_path: Path):
    text_file = tmp_path / "a.txt"
    text_file.write_text("hello")
    assert await convert_to_text(text_file) == text_file


@pytest.mark.asyncio
async def test_convert_to_text_copies_markdown(tmp_path: Path):
    markdown_file = tmp_path / "a.md"
    markdown_file.write_text("# hello")
    text_file = await convert_to_text(markdown_file)
    assert text_file == tmp_path / "a.txt"
    assert text_file.read_text() == "# hello"


@pytest.mark.asyncio
async def test_convert_to_text_converts_pdf_with_llm(tmp_path: Path):
    pdf_file = tmp_path / "a.pdf"
    pdf_file.write_bytes(b"%PDF")
    conversion = fake_pdf_conversion("converted")
    with patch(f"{MODULE}.convert_pdf_docx_pptx_to_markdown", conversion):
        text_file = await convert_to_text(pdf_file)
    conversion.assert_awaited_once_with(pdf_file)
    assert text_file.read_text() == "converted"


@pytest.mark.asyncio
async def test_convert_to_text_rejects_other_types(tmp_path: Path):
    with pytest.raises(ValueError):
        await convert_to_text(tmp_path / "a.docx")


@pytest.mark.asyncio
async def test_prepare_uploaded_file_uses_normalized_name(tmp_path: Path):
    prepared = await prepare_uploaded_file(uploaded("My Notes.MD", "notes"), tmp_path)
    assert prepared.uploaded_file_name == "My Notes.MD"
    assert prepared.original_file == tmp_path / "My_Notes.md"
    assert prepared.text_file.read_text() == "notes"


@pytest.mark.asyncio
async def test_replace_files_in_index_replaces_previous_versions(
    project_folder: Path, upload_dir: Path
):
    old_text = project_folder / INPUT_FOLDER / "My Report.txt"
    old_text.write_text("old")
    old_original = project_folder / ORIGINAL_INPUT_FOLDER / "My Report.pdf"
    old_original.write_bytes(b"old")
    rag = make_rag([("old_doc", old_text.resolve().as_posix())])
    statuses = []
    index = AsyncMock()
    extras = AsyncMock()

    with (
        patch(f"{MODULE}.initialize_rag", AsyncMock(return_value=rag)),
        patch(f"{MODULE}.lightrag_index", index),
        patch(
            f"{MODULE}.convert_pdf_docx_pptx_to_markdown",
            fake_pdf_conversion("new pdf"),
        ),
        patch("graphrag_kb_server.service.project.prepare_project_extras", extras),
    ):
        indexed_count = await replace_files_in_index(
            project_folder,
            [uploaded("My Report.pdf", "%PDF"), uploaded("notes.md", "notes")],
            lambda status, message: statuses.append(status),
            IndexingJobRegistry(),
        )

    assert indexed_count == 2
    assert statuses == [IndexingStatus.PREPARING, IndexingStatus.IN_PROGRESS]
    rag.adelete_by_doc_id.assert_awaited_once_with("old_doc")
    assert not old_text.exists()
    assert not old_original.exists()
    new_pdf_text = project_folder / INPUT_FOLDER / "My_Report.txt"
    new_notes_text = project_folder / INPUT_FOLDER / "notes.txt"
    assert new_pdf_text.read_text() == "new pdf"
    assert new_notes_text.read_text() == "notes"
    assert (
        project_folder / ORIGINAL_INPUT_FOLDER / "My_Report.pdf"
    ).read_bytes() == b"%PDF"
    assert (project_folder / ORIGINAL_INPUT_FOLDER / "notes.md").exists()
    index.assert_awaited_once_with(rag, [new_pdf_text, new_notes_text], tolerance=0)
    extras.assert_awaited_once_with(project_folder)
    assert read_project_status(project_folder) == IndexingStatus.COMPLETED
    assert list(upload_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_failed_conversion_leaves_project_unchanged(
    project_folder: Path, upload_dir: Path
):
    old_text = project_folder / INPUT_FOLDER / "report.txt"
    old_text.write_text("old")
    initialize = AsyncMock()
    failing_conversion = AsyncMock(side_effect=Exception("LLM unavailable"))

    with (
        patch(f"{MODULE}.initialize_rag", initialize),
        patch(f"{MODULE}.convert_pdf_docx_pptx_to_markdown", failing_conversion),
    ):
        with pytest.raises(Exception, match="LLM unavailable"):
            await replace_files_in_index(
                project_folder,
                [uploaded("report.pdf", "%PDF")],
                registry=IndexingJobRegistry(),
            )

    initialize.assert_not_awaited()
    assert old_text.read_text() == "old"
    assert not (project_folder / "project.json").exists()
    assert list(upload_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_failed_indexing_marks_project_as_failed(
    project_folder: Path, upload_dir: Path
):
    with (
        patch(f"{MODULE}.initialize_rag", AsyncMock(return_value=make_rag([]))),
        patch(f"{MODULE}.lightrag_index", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        with pytest.raises(RuntimeError):
            await replace_files_in_index(
                project_folder, [uploaded("a.txt", "a")], registry=IndexingJobRegistry()
            )

    assert read_project_status(project_folder) == IndexingStatus.FAILED


@pytest.mark.asyncio
async def test_run_indexing_job_records_completion(project_folder: Path):
    registry = IndexingJobRegistry()
    job = registry.create_job("t", project_folder.name, ["a.txt"])
    replace = AsyncMock(return_value=1)
    with patch(f"{MODULE}.replace_files_in_index", replace):
        await run_indexing_job(
            job.job_id, project_folder, [uploaded("a.txt", "a")], registry
        )

    finished_job = registry.get_job("t", job.job_id)
    assert finished_job.status == IndexingStatus.COMPLETED
    assert finished_job.message == "1 file(s) indexed successfully in index project"
    assert finished_job.error is None


@pytest.mark.asyncio
async def test_run_indexing_job_forwards_status_updates(project_folder: Path):
    registry = IndexingJobRegistry()
    job = registry.create_job("t", project_folder.name, ["a.txt"])
    seen_statuses = []

    async def replace(_folder, _files, on_status, _registry):
        on_status(IndexingStatus.IN_PROGRESS, "Indexing")
        seen_statuses.append(registry.get_job("t", job.job_id).status)
        return 1

    with patch(f"{MODULE}.replace_files_in_index", replace):
        await run_indexing_job(
            job.job_id, project_folder, [uploaded("a.txt", "a")], registry
        )

    assert seen_statuses == [IndexingStatus.IN_PROGRESS]


@pytest.mark.asyncio
async def test_run_indexing_job_records_failure(project_folder: Path):
    registry = IndexingJobRegistry()
    job = registry.create_job("t", project_folder.name, ["a.txt"])
    replace = AsyncMock(side_effect=RuntimeError("boom"))
    with patch(f"{MODULE}.replace_files_in_index", replace):
        await run_indexing_job(
            job.job_id, project_folder, [uploaded("a.txt", "a")], registry
        )

    failed_job = registry.get_job("t", job.job_id)
    assert failed_job.status == IndexingStatus.FAILED
    assert failed_job.error == "boom"


def test_module_exposes_allowed_extensions():
    assert lightrag_file_indexing.ALLOWED_INDEX_FILE_EXTENSIONS == {
        ".txt",
        ".md",
        ".pdf",
    }

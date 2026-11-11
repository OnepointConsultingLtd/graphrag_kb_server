import asyncio
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.indexing_job_registry import indexing_job_registry
from graphrag_kb_server.service.parser import clustre_scraper_common as common
from graphrag_kb_server.service.parser.clustre_scraper_common import (
    PLAIN_TEXT_TAG,
    extract_content_blocks,
    index_files_into_project,
    resolve_lightrag_project_dir,
    run_periodic_sync,
)

ARTICLE_BODY_HTML = """
<html><body>
<header><nav>Home About</nav></header>
<h1>Edge Computing</h1>
<div id=internalContent>
<p>Edge computing moves   processing closer to the data.</p>
<h2>Why it matters</h2>
<ul><li><p>Lower latency</p></li><li>Less bandwidth</li></ul>
<blockquote>The edge is the new cloud.</blockquote>
<p></p>
<div class=social-sharing><p>Share on Facebook</p><p>Share on Twitter</p></div>
</div>
<div class=footerStyle><p>Copyright Clustre</p></div>
</body></html>
"""


def test_extract_content_blocks_returns_leaf_blocks_without_noise():
    soup = BeautifulSoup(ARTICLE_BODY_HTML, "html.parser")
    assert extract_content_blocks(soup) == [
        ("p", "Edge computing moves processing closer to the data."),
        ("h2", "Why it matters"),
        ("p", "Lower latency"),
        ("li", "Less bandwidth"),
        ("blockquote", "The edge is the new cloud."),
    ]


def test_extract_content_blocks_falls_back_to_plain_text_lines():
    soup = BeautifulSoup(
        "<html><body><div id=internalContent>Just <br>text</div></body></html>",
        "html.parser",
    )
    assert extract_content_blocks(soup) == [
        (PLAIN_TEXT_TAG, "Just"),
        (PLAIN_TEXT_TAG, "text"),
    ]


def test_resolve_lightrag_project_dir_rejects_unsupported_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(common.cfg, "graphrag_root_dir_path", tmp_path)
    (tmp_path / "schema" / "graphrag" / "project").mkdir(parents=True)
    assert resolve_lightrag_project_dir("schema", "project", "graphrag") is None


def test_resolve_lightrag_project_dir_requires_existing_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(common.cfg, "graphrag_root_dir_path", tmp_path)
    assert resolve_lightrag_project_dir("schema", "project", "lightrag") is None
    project_dir = tmp_path / "schema" / "lightrag" / "project"
    project_dir.mkdir(parents=True)
    assert resolve_lightrag_project_dir("schema", "project", "lightrag") == project_dir


def _record_project_statuses(monkeypatch) -> list[IndexingStatus]:
    """Replace write_project_file with a fake which records the written statuses."""
    from graphrag_kb_server.service import project as project_service

    statuses: list[IndexingStatus] = []
    monkeypatch.setattr(
        project_service,
        "write_project_file",
        lambda project_dir, status: statuses.append(status),
    )
    return statuses


@pytest.mark.asyncio
async def test_index_files_into_project_marks_failure(monkeypatch, tmp_path):
    statuses = _record_project_statuses(monkeypatch)

    async def fake_initialize_rag(project_dir: Path):
        return object()

    async def failing_index(rag, files: list[Path]):
        raise RuntimeError("indexing failed")

    monkeypatch.setattr(common, "initialize_rag", fake_initialize_rag)
    monkeypatch.setattr(common, "lightrag_index", failing_index)
    with pytest.raises(RuntimeError, match="indexing failed"):
        await index_files_into_project(tmp_path, [tmp_path / "a.md"])
    assert statuses == [IndexingStatus.IN_PROGRESS, IndexingStatus.FAILED]
    assert not indexing_job_registry.project_lock(tmp_path).locked()


@pytest.mark.asyncio
async def test_index_files_into_project_holds_project_lock(monkeypatch, tmp_path):
    statuses = _record_project_statuses(monkeypatch)
    lock_held_while: dict[str, bool] = {}
    saved_files: list[Path] = []

    async def fake_initialize_rag(project_dir: Path):
        lock_held_while["initialize"] = indexing_job_registry.project_lock(
            project_dir
        ).locked()
        return object()

    async def fake_index(rag, files: list[Path]):
        lock_held_while["index"] = indexing_job_registry.project_lock(tmp_path).locked()

    async def fake_save_links(project_dir: Path, files: list[Path]):
        saved_files.extend(files)

    monkeypatch.setattr(common, "initialize_rag", fake_initialize_rag)
    monkeypatch.setattr(common, "lightrag_index", fake_index)
    monkeypatch.setattr(common, "save_links", fake_save_links)
    files = [tmp_path / "a.md", tmp_path / "b.md"]
    await index_files_into_project(tmp_path, files)
    assert lock_held_while == {"initialize": True, "index": True}
    assert saved_files == files
    assert statuses == [IndexingStatus.IN_PROGRESS, IndexingStatus.COMPLETED]
    assert not indexing_job_registry.project_lock(tmp_path).locked()


@pytest.mark.asyncio
async def test_index_files_into_project_without_files_does_nothing(monkeypatch, tmp_path):
    statuses = _record_project_statuses(monkeypatch)
    await index_files_into_project(tmp_path, [])
    assert statuses == []


@pytest.mark.asyncio
async def test_run_periodic_sync_survives_failures(monkeypatch):
    runs: list[int] = []
    sleeps: list[float] = []

    async def flaky_sync():
        runs.append(len(runs))
        if len(runs) == 1:
            raise RuntimeError("first run fails")

    async def fake_sleep(seconds: float):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(common.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await run_periodic_sync(flaky_sync, 24, "Test")
    assert runs == [0, 1]
    assert sleeps == [24 * 3600, 24 * 3600]

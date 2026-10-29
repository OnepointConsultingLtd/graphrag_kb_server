import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.indexing_job_registry import IndexingJobRegistry


def test_create_job_is_not_started():
    registry = IndexingJobRegistry()
    job = registry.create_job("tennant_a", "project", ["a.txt"])
    assert job.status == IndexingStatus.NOT_STARTED
    assert job.engine == Engine.LIGHTRAG
    assert job.file_names == ["a.txt"]
    assert registry.get_job("tennant_a", job.job_id) == job


def test_create_job_uses_unique_ids():
    registry = IndexingJobRegistry()
    first = registry.create_job("t", "p", ["a.txt"])
    second = registry.create_job("t", "p", ["a.txt"])
    assert first.job_id != second.job_id


def test_update_status_changes_status_message_and_error():
    registry = IndexingJobRegistry()
    job = registry.create_job("t", "p", ["a.txt"])
    updated = registry.update_status(
        job.job_id, IndexingStatus.FAILED, "failed", error="boom"
    )
    assert updated.status == IndexingStatus.FAILED
    assert updated.message == "failed"
    assert updated.error == "boom"
    assert updated.updated_at >= job.updated_at
    assert registry.get_job("t", job.job_id).status == IndexingStatus.FAILED


def test_update_status_of_unknown_job_returns_none():
    assert (
        IndexingJobRegistry().update_status("missing", IndexingStatus.COMPLETED) is None
    )


def test_get_job_hides_jobs_of_other_tennants():
    registry = IndexingJobRegistry()
    job = registry.create_job("tennant_a", "p", ["a.txt"])
    assert registry.get_job("tennant_b", job.job_id) is None
    assert registry.get_job("tennant_a", "unknown") is None


def test_model_dump_does_not_expose_tennant():
    job = IndexingJobRegistry().create_job("tennant_a", "p", ["a.txt"])
    dumped = job.model_dump()
    assert "tennant" not in dumped
    assert dumped["status"] == "not_started"
    assert isinstance(dumped["created_at"], str)


def test_prune_removes_only_old_finished_jobs():
    registry = IndexingJobRegistry(retention=timedelta(hours=1))
    old_finished = registry.create_job("t", "p", ["a.txt"])
    old_running = registry.create_job("t", "p", ["b.txt"])
    recent_finished = registry.create_job("t", "p", ["c.txt"])
    registry.update_status(old_finished.job_id, IndexingStatus.COMPLETED)
    registry.update_status(old_running.job_id, IndexingStatus.IN_PROGRESS)
    registry.update_status(recent_finished.job_id, IndexingStatus.FAILED)
    two_hours_ago = datetime.now() - timedelta(hours=2)
    for job_id in (old_finished.job_id, old_running.job_id):
        registry._jobs[job_id] = registry._jobs[job_id].model_copy(
            update={"updated_at": two_hours_ago}
        )

    assert registry.prune_finished_jobs() == 1
    assert registry.get_job("t", old_finished.job_id) is None
    assert registry.get_job("t", old_running.job_id) is not None
    assert registry.get_job("t", recent_finished.job_id) is not None


@pytest.mark.asyncio
async def test_run_in_background_runs_coroutine_and_releases_task():
    registry = IndexingJobRegistry()
    job = registry.create_job("t", "p", ["a.txt"])

    async def complete_job():
        registry.update_status(job.job_id, IndexingStatus.COMPLETED)

    task = registry.run_in_background(job.job_id, complete_job())
    assert task in registry._tasks
    await task
    await asyncio.sleep(0)
    assert registry.get_job("t", job.job_id).status == IndexingStatus.COMPLETED
    assert task not in registry._tasks


@pytest.mark.asyncio
async def test_cancel_all_cancels_running_tasks():
    registry = IndexingJobRegistry()
    task = registry.run_in_background("job", asyncio.sleep(60))
    await registry.cancel_all()
    assert task.cancelled()
    assert not registry._tasks


def test_project_lock_is_shared_per_project(tmp_path: Path):
    registry = IndexingJobRegistry()
    first_project = tmp_path / "first"
    assert registry.project_lock(first_project) is registry.project_lock(
        tmp_path / "x" / ".." / "first"
    )
    assert registry.project_lock(first_project) is not registry.project_lock(
        tmp_path / "second"
    )

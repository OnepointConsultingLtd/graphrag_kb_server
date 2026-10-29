import asyncio
import contextlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Coroutine

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.indexing_job import IndexingJob
from graphrag_kb_server.model.project import IndexingStatus

FINISHED_JOB_RETENTION = timedelta(hours=24)


class IndexingJobRegistry:
    """Keeps track of the indexing jobs which run in the background.

    The jobs are held in memory only, so they are lost when the server restarts.
    The registry also keeps a reference to every running task, so that the tasks
    are not garbage collected before they finish, and hands out one lock per
    project so that two jobs never modify the same LightRAG index concurrently.
    """

    def __init__(self, retention: timedelta = FINISHED_JOB_RETENTION):
        self._jobs: dict[str, IndexingJob] = {}
        self._tasks: set[asyncio.Task] = set()
        self._project_locks: dict[Path, asyncio.Lock] = {}
        self._retention = retention

    def create_job(
        self,
        tennant: str,
        project: str,
        file_names: list[str],
        engine: Engine = Engine.LIGHTRAG,
    ) -> IndexingJob:
        """Registers a new job which has not started yet.

        Finished jobs older than the retention period are removed at the same
        time, which keeps the memory used by the registry bounded.
        """
        self.prune_finished_jobs()
        now = datetime.now()
        job = IndexingJob(
            job_id=str(uuid.uuid4()),
            tennant=tennant,
            project=project,
            engine=engine,
            file_names=file_names,
            status=IndexingStatus.NOT_STARTED,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job.job_id] = job
        return job

    def update_status(
        self,
        job_id: str,
        status: IndexingStatus,
        message: str | None = None,
        error: str | None = None,
    ) -> IndexingJob | None:
        """Changes the status of a job.

        Returns:
            The updated job or None if the job is unknown.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(
            update={
                "status": status,
                "message": message,
                "error": error,
                "updated_at": datetime.now(),
            }
        )
        self._jobs[job_id] = updated_job
        return updated_job

    def get_job(self, tennant: str, job_id: str) -> IndexingJob | None:
        """Finds a job of a tennant.

        Returns:
            The job or None if it does not exist or belongs to another tennant.
        """
        job = self._jobs.get(job_id)
        if job is None or job.tennant != tennant:
            return None
        return job

    def prune_finished_jobs(self) -> int:
        """Removes the finished jobs which are older than the retention period.

        Returns:
            The number of removed jobs.
        """
        threshold = datetime.now() - self._retention
        expired_job_ids = [
            job_id
            for job_id, job in self._jobs.items()
            if job.is_finished and job.updated_at < threshold
        ]
        for job_id in expired_job_ids:
            del self._jobs[job_id]
        return len(expired_job_ids)

    def run_in_background(self, job_id: str, coroutine: Coroutine) -> asyncio.Task:
        """Runs a coroutine as a background task and keeps a reference to it.

        The reference is dropped as soon as the task finishes.
        """
        task = asyncio.create_task(coroutine, name=f"indexing_job_{job_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def cancel_all(self):
        """Cancels all running background tasks, e.g. when the server shuts down."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                try:
                    await task
                except Exception as e:
                    logger.error(f"Indexing task {task.get_name()} failed: {e}")
        self._tasks.clear()

    def project_lock(self, project_folder: Path) -> asyncio.Lock:
        """Returns the lock which serialises the indexing jobs of one project."""
        key = project_folder.resolve()
        if key not in self._project_locks:
            self._project_locks[key] = asyncio.Lock()
        return self._project_locks[key]


indexing_job_registry = IndexingJobRegistry()

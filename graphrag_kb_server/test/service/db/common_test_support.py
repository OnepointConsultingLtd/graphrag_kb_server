from pathlib import Path

from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import IndexingStatus
from datetime import datetime
from typing import Callable, Awaitable


DEFAULT_SCHEMA_NAME = "public"


def create_project_dir(schema_name: str, engine: Engine, project_name: str) -> Path:
    from graphrag_kb_server.config import cfg

    return cfg.graphrag_root_dir_path / schema_name / engine.value / project_name


async def create_test_project_wrapper(
    function: Callable[[FullProject, Project, str, str], Awaitable[None]]
):
    from graphrag_kb_server.service.db.db_persistence_project import (
        create_project,
        delete_project,
        create_project_table,
        drop_project_table,
        find_project_by_name,
    )

    project_name = "test_project"
    try:
        full_project = FullProject(
            schema_name=DEFAULT_SCHEMA_NAME,
            engine=Engine.LIGHTRAG,
            project=Project(
                name=project_name,
                updated_timestamp=datetime.now(),
                input_files=[],
                indexing_status=IndexingStatus.NOT_STARTED,
            ),
        )
        # Create project table, project, and topics table
        await create_project_table(DEFAULT_SCHEMA_NAME)
        await create_project(full_project)

        found_project = await find_project_by_name(
            DEFAULT_SCHEMA_NAME, full_project.project.name
        )

        assert found_project is not None
        assert found_project.id != full_project.id

        await function(full_project, found_project, DEFAULT_SCHEMA_NAME, project_name)

    finally:
        await delete_project(full_project)
        await drop_project_table(full_project)

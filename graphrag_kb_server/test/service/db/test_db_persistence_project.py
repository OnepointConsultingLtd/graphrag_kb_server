import pytest

from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import Project, IndexingStatus
from graphrag_kb_server.service.db.db_persistence_project import (
    create_project,
    project_exists,
    delete_project,
)
from datetime import datetime
from graphrag_kb_server.test.service.db.common_test_support import DEFAULT_SCHEMA_NAME


async def _create_test_project():
    test_project = FullProject(
        schema_name=DEFAULT_SCHEMA_NAME,
        engine=Engine.GRAPHRAG,
        project=Project(
            name="test_project",
            updated_timestamp=datetime.now(),
            input_files=[],
            indexing_status=IndexingStatus.NOT_STARTED,
        ),
    )
    await create_project(test_project)
    assert await project_exists(test_project) is True
    await delete_project(test_project)
    assert await project_exists(test_project) is False


@pytest.mark.asyncio
async def test_create_project():
    await _create_test_project()

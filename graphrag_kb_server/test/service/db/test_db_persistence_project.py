import pytest

from graphrag_kb_server.test.service.db.common_test_support import DEFAULT_SCHEMA_NAME


async def _create_test_project():
    from graphrag_kb_server.service.db.db_persistence_project import (
        create_project,
        project_exists,
        delete_project,
    )
    from graphrag_kb_server.test.service.db.project_provider import create_test_project
    test_project = create_test_project()
    await create_project(test_project)
    assert await project_exists(test_project) is True
    await delete_project(test_project)
    assert await project_exists(test_project) is False


@pytest.mark.asyncio
async def test_create_project():
    await _create_test_project()

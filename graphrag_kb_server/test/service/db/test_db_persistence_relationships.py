from pathlib import Path
import pytest

from graphrag_kb_server.test.service.db.common_test_support import DEFAULT_SCHEMA_NAME


async def _create_relationships_table(schema_name: str):
    from graphrag_kb_server.service.db.db_persistence_search import (
        create_search_history_tables,
    )
    from graphrag_kb_server.service.db.db_persistence_relationships import (
        create_relationships_table,
    )

    await create_search_history_tables(schema_name)
    await create_relationships_table(schema_name)


async def _drop_relationships_table(schema_name: str):
    from graphrag_kb_server.service.db.db_persistence_search import (
        drop_search_history_tables,
    )
    from graphrag_kb_server.service.db.db_persistence_relationships import (
        drop_relationships_table,
    )

    await drop_relationships_table(schema_name)
    await drop_search_history_tables(schema_name)


@pytest.mark.asyncio
async def test_create_drop_relationships_table():
    schema_name = DEFAULT_SCHEMA_NAME
    try:
        await _create_relationships_table(schema_name)
    finally:
        await _drop_relationships_table(schema_name)


@pytest.mark.asyncio
async def test_save_relationships():
    from graphrag_kb_server.service.db.db_persistence_relationships import (
        find_relationships,
        save_relationships,
    )
    from graphrag_kb_server.service.db.db_persistence_search import insert_search_query
    from graphrag_kb_server.test.service.db.search_history_provider import (
        create_search_history,
    )
    from graphrag_kb_server.service.db.db_persistence_project import create_project
    from graphrag_kb_server.test.service.db.project_provider import create_test_project
    from graphrag_kb_server.model.search.relationships import RelationshipsJSON

    schema_name = DEFAULT_SCHEMA_NAME
    try:
        await _create_relationships_table(schema_name)
        test_project = create_test_project()
        await create_project(test_project)
        search_history = create_search_history()
        search_history_id = await insert_search_query(
            Path(f"/var/graphrag/tennants/public/graphrag/{test_project.project.name}"),
            search_history,
        )
        relationships = RelationshipsJSON(
            relationships='{"test_relationship": "test_value"}',
            search_id=search_history_id,
        )
        await save_relationships(schema_name, relationships)
        found_relationships = await find_relationships(schema_name, search_history_id)
        assert found_relationships == relationships
    finally:
        await _drop_relationships_table(schema_name)

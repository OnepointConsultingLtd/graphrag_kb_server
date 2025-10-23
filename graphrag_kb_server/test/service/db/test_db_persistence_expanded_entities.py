import pytest

from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.service.db.db_persistence_expanded_entities import (
    create_expanded_entities_table,
    drop_expanded_entities_table,
    insert_expanded_entities,
    get_expanded_entities,
)
from graphrag_kb_server.test.model.match_query_provider import (
    create_match_query,
    create_match_output,
)
from graphrag_kb_server.test.service.db.test_topics_table import (
    create_test_project_wrapper,
)
from graphrag_kb_server.test.service.db.common_test_support import create_project_dir


@pytest.mark.asyncio
async def test_create_expanded_entities():

    async def test_function(
        full_project: FullProject, _: Project, schema_name: str, project_name: str
    ):
        fake_project_dir = create_project_dir(
            schema_name, full_project.engine, project_name
        )
        try:
            await create_expanded_entities_table(schema_name)
            match_query = create_match_query()
            match_output = create_match_output()
            digest = await insert_expanded_entities(
                fake_project_dir, match_query, match_output
            )
            assert digest is not None
            mached_output_from_db = await get_expanded_entities(
                fake_project_dir, match_query
            )
            assert mached_output_from_db is not None
            assert mached_output_from_db.model_dump() == match_output.model_dump()
        finally:
            await drop_expanded_entities_table(schema_name)

    await create_test_project_wrapper(test_function)

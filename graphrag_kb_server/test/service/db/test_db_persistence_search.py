import pytest

from graphrag_kb_server.service.db.db_persistence_search import (
    create_search_history_tables,
    drop_search_history_tables,
    get_search_results,
)
from graphrag_kb_server.test.provider.search_provider import (
    create_document_search_query,
    create_search_results,
)
from graphrag_kb_server.test.service.db.test_topics_table import (
    create_test_project_wrapper,
)
from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.test.service.db.common_test_support import (
    create_project_dir,
    DEFAULT_SCHEMA_NAME,
)
from graphrag_kb_server.service.db.db_persistence_search import (
    insert_search_query,
    update_search_query_with_response,
    insert_search_results,
)


@pytest.mark.asyncio
async def test_create_drop_search_history_tables():
    schema_name = DEFAULT_SCHEMA_NAME
    try:
        await create_search_history_tables(schema_name)
    finally:
        await drop_search_history_tables(schema_name)


@pytest.mark.asyncio
async def test_insert_search_query():

    async def test_function(
        full_project: FullProject, _: Project, schema_name: str, project_name: str
    ):
        try:
            await create_search_history_tables(schema_name)
            project_dir = create_project_dir(
                schema_name, full_project.engine, project_name
            )
            document_search_query = create_document_search_query()
            search_history_id = await insert_search_query(
                project_dir, document_search_query
            )
            assert search_history_id is not None
            assert search_history_id > 0
            updated_count = await update_search_query_with_response(
                project_dir, search_history_id, "Test response"
            )
            assert updated_count is not None
            assert updated_count > 0
            search_results = create_search_results()
            search_results_ids = await insert_search_results(
                project_dir, search_history_id, search_results
            )
            assert search_results_ids is not None
            assert len(search_results_ids) > 0
            assert search_results_ids[0] > 0
            found_search_results = await get_search_results(
                project_dir, document_search_query
            )
            assert found_search_results is not None
            assert found_search_results.request_id == document_search_query.request_id
            assert found_search_results.response == "Test response"
            assert len(found_search_results.documents) == len(search_results.documents)
            for document in found_search_results.documents:
                assert document.summary == search_results.documents[0].summary
                assert document.relevance == search_results.documents[0].relevance
        finally:
            await drop_search_history_tables(schema_name)

    await create_test_project_wrapper(test_function)

import pytest

from graphrag_kb_server.model.document_trend_result import DocumentTrendResult, TrendClass
from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trend_result(document_path: str, project_id: int) -> DocumentTrendResult:
    return DocumentTrendResult(
        document_path=document_path,
        project_id=project_id,
        main_topics=["AI governance", "MLOps"],
        trend_class=TrendClass.RISING,
        confidence=0.85,
        reasoning="Strong growth in recent publications.",
        recent_findings="Several major conferences covered this topic last month.",
        visited_urls=["https://example.com/a", "https://example.com/b"],
    )


# ---------------------------------------------------------------------------
# DDL: create / drop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_drop_document_trend_result_table():
    """Table can be created and then dropped without error."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        try:
            await create_document_trend_result_table(schema_name)
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Insert + retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_and_retrieve_trend_result():
    """An inserted trend result can be retrieved within its expiry window."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
        insert_document_trend_result,
        get_document_trend_result_by_path,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        try:
            await create_document_trend_result_table(schema_name)
            result = _trend_result("/input/doc.txt", project_id)
            await insert_document_trend_result(schema_name, result)

            fetched = await get_document_trend_result_by_path(
                schema_name, "/input/doc.txt", project_name, expiry_period_in_days=30
            )
            assert fetched is not None
            assert fetched.document_path == "/input/doc.txt"
            assert fetched.trend_class == TrendClass.RISING
            assert fetched.confidence == pytest.approx(0.85)
            assert fetched.main_topics == ["AI governance", "MLOps"]
            assert fetched.visited_urls == [
                "https://example.com/a",
                "https://example.com/b",
            ]
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_missing_path_returns_none():
    """Lookup for a document path with no stored result returns None."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
        get_document_trend_result_by_path,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        try:
            await create_document_trend_result_table(schema_name)
            fetched = await get_document_trend_result_by_path(
                schema_name,
                "/input/nonexistent.txt",
                project_name,
                expiry_period_in_days=30,
            )
            assert fetched is None
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Upsert behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_is_upsert():
    """Re-inserting for the same (document_path, project_id) updates the row; count stays 1."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
        insert_document_trend_result,
        get_document_trend_result_by_path,
    )
    from graphrag_kb_server.service.db.connection_pool import fetch_one

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        try:
            await create_document_trend_result_table(schema_name)
            await insert_document_trend_result(
                schema_name, _trend_result("/input/doc.txt", project_id)
            )

            updated = DocumentTrendResult(
                document_path="/input/doc.txt",
                project_id=project_id,
                main_topics=["New topic"],
                trend_class=TrendClass.HOT,
                confidence=0.99,
                reasoning="Updated reasoning.",
                recent_findings="Updated findings.",
                visited_urls=["https://example.com/new"],
            )
            await insert_document_trend_result(schema_name, updated)

            row_count = await fetch_one(
                f"SELECT COUNT(*) AS cnt FROM {schema_name}.TB_DOCUMENT_TREND_RESULT WHERE DOCUMENT_PATH = $1 AND PROJECT_ID = $2;",
                "/input/doc.txt",
                project_id,
            )
            assert row_count["cnt"] == 1

            fetched = await get_document_trend_result_by_path(
                schema_name, "/input/doc.txt", project_name, expiry_period_in_days=30
            )
            assert fetched is not None
            assert fetched.trend_class == TrendClass.HOT
            assert fetched.confidence == pytest.approx(0.99)
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_result_is_deleted_and_none_returned():
    """A result whose UPDATED_AT predates the expiry window is deleted on lookup and None is returned."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
        insert_document_trend_result,
        get_document_trend_result_by_path,
    )
    from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_one

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        try:
            await create_document_trend_result_table(schema_name)
            await insert_document_trend_result(
                schema_name, _trend_result("/input/old.txt", project_id)
            )

            # Back-date UPDATED_AT to simulate an expired record (31 days old)
            await execute_query(
                f"UPDATE {schema_name}.TB_DOCUMENT_TREND_RESULT SET UPDATED_AT = now() - interval '31 days' WHERE DOCUMENT_PATH = $1 AND PROJECT_ID = $2;",
                "/input/old.txt",
                project_id,
            )

            fetched = await get_document_trend_result_by_path(
                schema_name, "/input/old.txt", project_name, expiry_period_in_days=30
            )
            assert fetched is None

            # Confirm the row was physically deleted
            remaining = await fetch_one(
                f"SELECT 1 FROM {schema_name}.TB_DOCUMENT_TREND_RESULT WHERE DOCUMENT_PATH = $1 AND PROJECT_ID = $2;",
                "/input/old.txt",
                project_id,
            )
            assert remaining is None
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# FK cascade on project deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trend_results_deleted_when_project_is_removed():
    """Trend results are removed via FK cascade when their parent project row is deleted."""
    from graphrag_kb_server.service.db.db_persistence_trend_result import (
        create_document_trend_result_table,
        drop_document_trend_result_table,
        insert_document_trend_result,
        get_document_trend_result_by_path,
    )
    from graphrag_kb_server.service.db.db_persistence_project import delete_project

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        try:
            await create_document_trend_result_table(schema_name)
            await insert_document_trend_result(
                schema_name, _trend_result("/input/doc.txt", project_id)
            )

            await delete_project(full_project)

            fetched = await get_document_trend_result_by_path(
                schema_name, "/input/doc.txt", project_name, expiry_period_in_days=30
            )
            assert fetched is None
        finally:
            await drop_document_trend_result_table(schema_name)

    await create_test_project_wrapper(test_function)

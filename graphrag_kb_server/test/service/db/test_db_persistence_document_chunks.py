import pytest

from graphrag_kb_server.model.document_chunk import DocumentChunk
from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    document_path: str, project_id: int, *, chunk_id: str = "chunk-abc123"
) -> DocumentChunk:
    return DocumentChunk(
        document_path=document_path,
        chunk_content="Sample chunk content for testing.",
        chunk_id=chunk_id,
        project_id=project_id,
    )


# ---------------------------------------------------------------------------
# DDL: create / drop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_drop_document_chunks_table():
    """Table can be created and then dropped without error."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        try:
            await create_document_chunks_table(schema_name)
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Insert + retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_and_retrieve_chunk():
    """An inserted chunk can be retrieved by document_path and project_id."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        insert_document_chunk,
        get_document_chunks_by_path,
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
            await create_document_chunks_table(schema_name)
            chunk = _chunk("/input/doc1.txt", project_id)
            await insert_document_chunk(schema_name, chunk)

            results = await get_document_chunks_by_path(
                schema_name, "/input/doc1.txt", project_id
            )
            assert len(results) == 1
            assert results[0].document_path == "/input/doc1.txt"
            assert results[0].chunk_content == chunk.chunk_content
            assert results[0].chunk_id == chunk.chunk_id
            assert results[0].project_id == project_id
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_get_chunks_returns_empty_for_unknown_path():
    """Querying an unknown document path returns an empty list."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        get_document_chunks_by_path,
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
            await create_document_chunks_table(schema_name)
            results = await get_document_chunks_by_path(
                schema_name, "/nonexistent.txt", project_id
            )
            assert results == []
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_duplicate_is_ignored():
    """Inserting the same (document_path, project_id) twice does not raise and row count stays 1."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        insert_document_chunk,
        get_document_chunks_by_path,
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
            await create_document_chunks_table(schema_name)
            chunk = _chunk("/input/doc1.txt", project_id)
            await insert_document_chunk(schema_name, chunk)
            await insert_document_chunk(schema_name, chunk)

            results = await get_document_chunks_by_path(
                schema_name, "/input/doc1.txt", project_id
            )
            assert len(results) == 1
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# get_stored_document_paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stored_document_paths():
    """Returns the correct set of document paths for the project."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        insert_document_chunk,
        get_stored_document_paths,
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
            await create_document_chunks_table(schema_name)
            await insert_document_chunk(
                schema_name, _chunk("/input/a.txt", project_id, chunk_id="chunk-a")
            )
            await insert_document_chunk(
                schema_name, _chunk("/input/b.txt", project_id, chunk_id="chunk-b")
            )

            paths = await get_stored_document_paths(schema_name, project_id)
            assert paths == {"/input/a.txt", "/input/b.txt"}
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_get_stored_document_paths_returns_empty_when_no_chunks():
    """Returns an empty set when no chunks have been stored for the project."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        get_stored_document_paths,
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
            await create_document_chunks_table(schema_name)
            paths = await get_stored_document_paths(schema_name, project_id)
            assert paths == set()
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# FK cascade on project deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chunks_deleted_when_project_is_removed():
    """Chunks are removed via FK cascade when their parent project row is deleted."""
    from graphrag_kb_server.service.db.db_persistence_document_chunks import (
        create_document_chunks_table,
        drop_document_chunks_table,
        insert_document_chunk,
        get_document_chunks_by_path,
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
            await create_document_chunks_table(schema_name)
            await insert_document_chunk(
                schema_name, _chunk("/input/doc.txt", project_id)
            )

            # Delete the project; cascade should remove the chunk row
            await delete_project(full_project)

            results = await get_document_chunks_by_path(
                schema_name, "/input/doc.txt", project_id
            )
            assert results == []
        finally:
            await drop_document_chunks_table(schema_name)

    await create_test_project_wrapper(test_function)

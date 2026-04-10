from datetime import datetime, timezone, timedelta

import pytest

from graphrag_kb_server.model.path_properties import PathProperties
from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _props(path: str, project_id: int, *, days_ago: int = 0) -> PathProperties:
    modified = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return PathProperties(path=path, project_id=project_id, last_modified=modified)


# ---------------------------------------------------------------------------
# DDL: create / drop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_drop_path_properties_table():
    """Table can be created and then dropped without error."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        try:
            await create_path_properties_table(schema_name)
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Upsert + find_path_properties
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_and_find_single_record():
    """A single upserted record can be retrieved by path and project_id."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_path_properties,
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
            await create_path_properties_table(schema_name)
            props = _props("/docs/report.pdf", project_id)
            await upsert_path_properties(schema_name, [props])

            found = await find_path_properties(schema_name, "/docs/report.pdf", project_id)
            assert found is not None
            assert found.path == "/docs/report.pdf"
            assert found.project_id == project_id
            assert found.last_modified is not None
            assert found.last_modified.year == 2024
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_upsert_empty_list_does_nothing():
    """Upserting an empty list does not raise and leaves the table empty."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_all_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id

        try:
            await create_path_properties_table(schema_name)
            await upsert_path_properties(schema_name, [])
            found = await find_all_path_properties(schema_name, project_id)
            assert found == []
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_upsert_multiple_records():
    """Multiple records are all persisted and retrievable."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_all_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id

        try:
            await create_path_properties_table(schema_name)
            records = [
                _props("/docs/a.pdf", project_id, days_ago=0),
                _props("/docs/b.docx", project_id, days_ago=10),
                _props("/docs/c.txt", project_id, days_ago=20),
            ]
            await upsert_path_properties(schema_name, records)
            found = await find_all_path_properties(schema_name, project_id)
            assert len(found) == 3
            paths = {f.path for f in found}
            assert paths == {"/docs/a.pdf", "/docs/b.docx", "/docs/c.txt"}
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Upsert updates LAST_MODIFIED on conflict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_updates_last_modified_on_conflict():
    """Re-upserting the same path updates LAST_MODIFIED rather than inserting a duplicate."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_path_properties,
        find_all_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        path = "/docs/evolving.pdf"

        try:
            await create_path_properties_table(schema_name)

            original = _props(path, project_id, days_ago=30)
            await upsert_path_properties(schema_name, [original])

            updated_date = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
            updated = PathProperties(path=path, project_id=project_id, last_modified=updated_date)
            await upsert_path_properties(schema_name, [updated])

            all_records = await find_all_path_properties(schema_name, project_id)
            assert len(all_records) == 1, "ON CONFLICT should update, not insert a duplicate"

            found = await find_path_properties(schema_name, path, project_id)
            assert found is not None
            assert found.last_modified is not None
            assert found.last_modified.year == 2025
            assert found.last_modified.month == 1
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# find_path_properties — miss cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_path_properties_returns_none_for_unknown_path():
    """Querying a path that was never inserted returns None."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        find_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id

        try:
            await create_path_properties_table(schema_name)
            found = await find_path_properties(schema_name, "/no/such/file.pdf", project_id)
            assert found is None
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_find_path_properties_returns_none_for_wrong_project():
    """A record exists for one project_id but not for a different one."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        path = "/docs/scoped.pdf"

        try:
            await create_path_properties_table(schema_name)
            await upsert_path_properties(schema_name, [_props(path, project_id)])

            other_project_id = project_id + 99999
            found = await find_path_properties(schema_name, path, other_project_id)
            assert found is None

            found_correct = await find_path_properties(schema_name, path, project_id)
            assert found_correct is not None
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)


# ---------------------------------------------------------------------------
# Timezone-aware datetime round-trip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_last_modified_timezone_roundtrip():
    """last_modified survives a round-trip through the database as UTC."""
    from graphrag_kb_server.service.db.db_persistence_path_properties import (
        create_path_properties_table,
        drop_path_properties_table,
        upsert_path_properties,
        find_path_properties,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        # Use a non-UTC offset to verify that conversion is handled correctly
        cet = timezone(timedelta(hours=2))
        original_dt = datetime(2023, 11, 20, 14, 30, 0, tzinfo=cet)
        path = "/docs/tz_test.docx"

        try:
            await create_path_properties_table(schema_name)
            props = PathProperties(path=path, project_id=project_id, last_modified=original_dt)
            await upsert_path_properties(schema_name, [props])

            found = await find_path_properties(schema_name, path, project_id)
            assert found is not None
            assert found.last_modified is not None
            # Value stored as UTC naive, retrieved with UTC tzinfo attached
            expected_utc = original_dt.astimezone(timezone.utc)
            assert found.last_modified.year == expected_utc.year
            assert found.last_modified.month == expected_utc.month
            assert found.last_modified.day == expected_utc.day
            assert found.last_modified.hour == expected_utc.hour
        finally:
            await drop_path_properties_table(schema_name)

    await create_test_project_wrapper(test_function)

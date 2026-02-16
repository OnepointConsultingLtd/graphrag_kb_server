import pytest

from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.model.project import FullProject

from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
)


@pytest.mark.asyncio
async def test_create_and_drop_links_table():
    """Create links table then drop it (requires projects table for FK)."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        try:
            await create_path_links_table(schema_name)
            await drop_links_table_table(schema_name)
        except Exception:
            raise

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_save_path_links_and_find_path_links():
    """Save path links and retrieve them by project_id."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
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
            await create_path_links_table(schema_name)
            path_links = [
                PathLink(
                    path="/doc/a", link="https://example.com/a", project_id=project_id
                ),
                PathLink(
                    path="/doc/b", link="https://example.com/b", project_id=project_id
                ),
            ]
            await save_path_links(schema_name, path_links)
            found = await find_path_links(schema_name, project_id)
            assert len(found) == 2
            paths_links = {(p.path, p.link) for p in found}
            assert paths_links == {
                ("/doc/a", "https://example.com/a"),
                ("/doc/b", "https://example.com/b"),
            }
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_save_path_links_empty_list():
    """Saving empty list then find returns empty list."""

    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
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
            await create_path_links_table(schema_name)
            await save_path_links(schema_name, [])
            found = await find_path_links(schema_name, project_id)
            assert found == []
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_save_path_links_on_conflict_do_nothing():
    """Saving the same (path, link, project_id) twice does not duplicate due to ON CONFLICT DO NOTHING."""

    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
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
            await create_path_links_table(schema_name)
            link = PathLink(
                path="/doc/one", link="https://example.com/one", project_id=project_id
            )
            await save_path_links(schema_name, [link])
            await save_path_links(schema_name, [link])
            found = await find_path_links(schema_name, project_id)
            assert len(found) == 1
            assert found[0].path == link.path and found[0].link == link.link
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_find_path_links_returns_only_for_project():
    """find_path_links returns only links for the given project_id."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
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
            await create_path_links_table(schema_name)
            await save_path_links(
                schema_name,
                [
                    PathLink(
                        path="/doc/only",
                        link="https://example.com/only",
                        project_id=project_id,
                    )
                ],
            )
            # Query for a different project_id should return empty
            other_id = project_id + 99999
            found_other = await find_path_links(schema_name, other_id)
            assert found_other == []
            found_this = await find_path_links(schema_name, project_id)
            assert len(found_this) == 1
            assert found_this[0].path == "/doc/only"
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)

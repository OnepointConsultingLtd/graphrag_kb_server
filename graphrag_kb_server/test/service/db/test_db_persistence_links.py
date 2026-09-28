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
                    path="/doc/a",
                    link="https://vimeo.com/manage/videos/1045136579",
                    website_link="https://example.com",
                    project_id=project_id,
                ),
                PathLink(
                    path="/doc/b", link="https://example.com/b", project_id=project_id
                ),
            ]
            await save_path_links(schema_name, path_links)
            found = await find_path_links(schema_name, project_id)
            assert len(found) == 2
            paths_links = {(p.path, p.link, p.website_link, p.vimeo_id) for p in found}
            assert paths_links == {
                (
                    "/doc/a",
                    "https://vimeo.com/manage/videos/1045136579",
                    "https://example.com",
                    "1045136579",
                ),
                ("/doc/b", "https://example.com/b", None, None),
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


def test_extract_vimeo_id():
    from graphrag_kb_server.service.db.db_persistence_links import extract_vimeo_id

    assert extract_vimeo_id("https://vimeo.com/676029919") == "676029919"
    assert (
        extract_vimeo_id("https://vimeo.com/manage/videos/1045136579") == "1045136579"
    )
    assert extract_vimeo_id("//player.vimeo.com/video/676029919?title=0") == "676029919"
    assert extract_vimeo_id("https://example.com/676029919") is None


@pytest.mark.asyncio
async def test_replace_website_path_links_keeps_other_links():
    """Website links are set on rows matching the Vimeo id, other rows stay unset."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
        replace_website_path_links,
    )

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        article = "https://www.clustre.net/a/"

        try:
            await create_path_links_table(schema_name)
            await save_path_links(
                schema_name,
                [
                    PathLink(
                        path="/doc/video.txt",
                        link="https://vimeo.com/manage/videos/1045136579",
                        project_id=project_id,
                    ),
                    PathLink(
                        path="/doc/file.txt",
                        link="https://example.com/doc",
                        project_id=project_id,
                    ),
                ],
            )
            missing = await replace_website_path_links(
                schema_name, project_id, {article: ["https://vimeo.com/1045136579"]}
            )
            assert missing == {}
            found = await find_path_links(schema_name, project_id)
            assert {(p.path, p.website_link) for p in found} == {
                ("/doc/video.txt", article),
                ("/doc/file.txt", None),
            }
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_replace_website_path_links_returns_missing():
    """Entries whose Vimeo id has no row in the project are returned."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        replace_website_path_links,
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
                        path="/doc/video.txt",
                        link="https://vimeo.com/1045136579",
                        project_id=project_id,
                    )
                ],
            )
            missing = await replace_website_path_links(
                schema_name,
                project_id,
                {
                    "https://www.clustre.net/a/": [
                        "https://vimeo.com/1045136579",
                        "https://vimeo.com/676029919",
                    ],
                    "https://www.clustre.net/b/": ["https://vimeo.com/111"],
                    "https://www.clustre.net/c/": ["https://example.com/no-id"],
                },
            )
            assert missing == {
                "https://www.clustre.net/a/": ["https://vimeo.com/676029919"],
                "https://www.clustre.net/b/": ["https://vimeo.com/111"],
                "https://www.clustre.net/c/": ["https://example.com/no-id"],
            }
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_save_links_with_files(tmp_path, monkeypatch):
    """save_links(files=...) saves links from those files even if the project has links."""
    from graphrag_kb_server.model.engines import Engine
    from graphrag_kb_server.service import link_extraction_service
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        find_path_links,
    )
    from graphrag_kb_server.test.service.db.common_test_support import (
        create_project_dir,
    )

    async def always_valid(link: str) -> bool:
        return True

    monkeypatch.setattr(link_extraction_service, "verify_link", always_valid)

    async def test_function(
        full_project: FullProject,
        found_project: FullProject,
        schema_name: str,
        project_name: str,
    ):
        project_id = found_project.id
        assert project_id is not None
        transcript = tmp_path / "feb-22-it-edit_676029919.txt"
        transcript.write_text(
            "Video: https://vimeo.com/676029919\n"
            "Web page: https://www.clustre.net/feb-22-it-edit/\n\nHello",
            encoding="utf-8",
        )

        try:
            await create_path_links_table(schema_name)
            await save_path_links(
                schema_name,
                [
                    PathLink(
                        path="/doc/existing.txt",
                        link="https://example.com/existing",
                        project_id=project_id,
                    )
                ],
            )
            await link_extraction_service.save_links(
                create_project_dir(schema_name, Engine.LIGHTRAG, project_name),
                files=[transcript],
            )
            found = await find_path_links(schema_name, project_id)
            assert {(p.path, p.link, p.vimeo_id) for p in found} == {
                ("/doc/existing.txt", "https://example.com/existing", None),
                (transcript.as_posix(), "https://vimeo.com/676029919", "676029919"),
                (
                    transcript.as_posix(),
                    "https://www.clustre.net/feb-22-it-edit/",
                    None,
                ),
            }
        finally:
            await drop_links_table_table(schema_name)

    await create_test_project_wrapper(test_function)


@pytest.mark.asyncio
async def test_extract_all_vimeo_ids():
    """Returns distinct, sorted Vimeo ids and ignores links that are not Vimeo."""
    from graphrag_kb_server.service.db.db_persistence_links import (
        create_path_links_table,
        drop_links_table_table,
        save_path_links,
        extract_all_vimeo_ids,
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
                    PathLink(path=path, link=link, project_id=project_id)
                    for path, link in [
                        ("/doc/a", "https://vimeo.com/676029919"),
                        ("/doc/b", "https://vimeo.com/676029919"),
                        ("/doc/c", "https://vimeo.com/manage/videos/1045136579"),
                        ("/doc/d", "https://example.com/d"),
                    ]
                ],
            )
            assert await extract_all_vimeo_ids(schema_name) == [
                "1045136579",
                "676029919",
            ]
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

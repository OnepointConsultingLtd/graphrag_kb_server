import logging
import re

from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    init_pool,
)


TB_PATH_LINKS = "TB_PATH_LINKS"

logger = logging.getLogger(__name__)

VIMEO_ID_PATTERN = re.compile(r"vimeo\.com/(?:manage/videos/|video/)?(\d+)")


def extract_vimeo_id(link: str) -> str | None:
    match = VIMEO_ID_PATTERN.search(link)
    return match.group(1) if match else None


async def create_path_links_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PATH_LINKS} (
	ID SERIAL NOT NULL,
	PATH CHARACTER VARYING(4096) NOT NULL,
	LINK CHARACTER VARYING(4096) NOT NULL,
	WEBSITE_LINK CHARACTER VARYING(4096) NULL,
	VIMEO_ID CHARACTER VARYING(64) NULL,
    PROJECT_ID INTEGER NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (PATH, LINK, PROJECT_ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )
    await execute_query(
        f"""
ALTER TABLE {schema_name}.{TB_PATH_LINKS}
ADD COLUMN IF NOT EXISTS WEBSITE_LINK CHARACTER VARYING(4096) NULL;
"""
    )
    await execute_query(
        f"""
ALTER TABLE {schema_name}.{TB_PATH_LINKS}
ADD COLUMN IF NOT EXISTS VIMEO_ID CHARACTER VARYING(64) NULL;
"""
    )
    await execute_query(
        f"""
UPDATE {schema_name}.{TB_PATH_LINKS}
SET VIMEO_ID = substring(LINK from $1)
WHERE VIMEO_ID IS NULL AND LINK LIKE '%vimeo.com/%';
""",
        VIMEO_ID_PATTERN.pattern,
    )


async def drop_links_table_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_PATH_LINKS};
"""
    )


async def save_path_links(
    schema_name: str, path_links: list[PathLink], insert_if_not_exists: bool = False
):
    pool = await init_pool()
    if insert_if_not_exists and len(path_links) > 0:
        # check first path link
        first_path_link = path_links[0]
        count = await execute_query_with_return(
            f"""
            SELECT COUNT(*) FROM {schema_name}.{TB_PATH_LINKS} WHERE PROJECT_ID = $1;
            """,
            first_path_link.project_id,
        )
        if count > 0:
            return

    async with pool.acquire() as conn:
        for link in path_links:
            await conn.execute(
                f"""
        INSERT INTO {schema_name}.{TB_PATH_LINKS} (PATH, LINK, WEBSITE_LINK, VIMEO_ID, PROJECT_ID) VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (PATH, LINK, PROJECT_ID) DO NOTHING;
        """,
                link.path,
                link.link,
                link.website_link,
                extract_vimeo_id(link.link),
                link.project_id,
            )


async def replace_website_path_links(
    schema_name: str, project_id: int, path_links: dict[str, list[str]]
) -> dict[str, list[str]]:
    """Returns the input entries whose Vimeo id matched no row of the project."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                f"""
UPDATE {schema_name}.{TB_PATH_LINKS} SET WEBSITE_LINK = NULL WHERE PROJECT_ID = $1;
""",
                project_id,
            )
            list_of_tuples = [
                (vimeo_id, website_link, project_id)
                for website_link, vimeo_links in path_links.items()
                for vimeo_link in vimeo_links
                if (vimeo_id := extract_vimeo_id(vimeo_link)) is not None
            ]
            for vimeo_id, website_link, project_id in list_of_tuples:
                print(
                    f"UPDATE {schema_name}.{TB_PATH_LINKS} SET WEBSITE_LINK = '{website_link}' WHERE PROJECT_ID = {project_id} AND VIMEO_ID = '{vimeo_id}';"
                )
            await conn.executemany(
                f"""
UPDATE {schema_name}.{TB_PATH_LINKS} SET WEBSITE_LINK = $2 WHERE PROJECT_ID = $3 AND VIMEO_ID = $1;
""",
                list_of_tuples,
            )
            found_rows = await conn.fetch(
                f"""
SELECT DISTINCT VIMEO_ID FROM {schema_name}.{TB_PATH_LINKS} WHERE PROJECT_ID = $1 AND VIMEO_ID = ANY($2);
""",
                project_id,
                [vimeo_id for vimeo_id, _, _ in list_of_tuples],
            )
    found_ids = {row["vimeo_id"] for row in found_rows}
    missing: dict[str, list[str]] = {}
    for website_link, vimeo_links in path_links.items():
        for vimeo_link in vimeo_links:
            if extract_vimeo_id(vimeo_link) not in found_ids:
                missing.setdefault(website_link, []).append(vimeo_link)
    return missing


async def find_path_links(schema_name: str, project_id: int) -> list[PathLink]:
    pool = await init_pool()
    async with pool.acquire() as conn:
        path_links = []
        results = await conn.fetch(
            f"""
SELECT * FROM {schema_name}.{TB_PATH_LINKS} WHERE PROJECT_ID = $1;
""",
            project_id,
        )
        for result in results:
            path_links.append(
                PathLink(
                    path=result["path"],
                    link=result["link"],
                    website_link=result["website_link"],
                    vimeo_id=result["vimeo_id"],
                    project_id=result["project_id"],
                )
            )
        return path_links


async def extract_all_vimeo_ids(schema_name: str) -> list[str]:
    pool = await init_pool()
    async with pool.acquire() as conn:
        results = await conn.fetch(
            f"""
SELECT DISTINCT VIMEO_ID FROM {schema_name}.{TB_PATH_LINKS}
WHERE VIMEO_ID IS NOT NULL ORDER BY VIMEO_ID;
"""
        )
        return [result["vimeo_id"] for result in results]


async def get_links_by_path(schema_name: str, project_id: int, path: str) -> list[str]:
    logger.info(
        f"Getting links by path {path} for project {project_id} in schema {schema_name}"
    )
    pool = await init_pool()
    async with pool.acquire() as conn:
        results = await conn.fetch(
            f"""
            SELECT LINK FROM {schema_name}.{TB_PATH_LINKS} WHERE PROJECT_ID = $1 AND PATH = $2;
            """,
            project_id,
            path,
        )
        return [result["link"] for result in results]

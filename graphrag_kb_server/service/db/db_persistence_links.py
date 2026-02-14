

from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.service.db.connection_pool import execute_query, init_pool


TB_PATH_LINKS = "TB_PATH_LINKS"

async def create_links_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PATH_LINKS} (
	ID SERIAL NOT NULL,
	PATH CHARACTER VARYING(4096) NOT NULL,
	LINK CHARACTER VARYING(4096) NOT NULL,
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


async def drop_links_table_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_PATH_LINKS};
"""
    )


async def save_path_links(schema_name: str, path_links: list[PathLink]):
    pool = await init_pool()
    async with pool.acquire() as conn:
        for link in path_links:
            await conn.execute(
                f"""
        INSERT INTO {schema_name}.{TB_PATH_LINKS} (PATH, LINK, PROJECT_ID) VALUES ($1, $2, $3)
        ON CONFLICT (PATH, LINK, PROJECT_ID) DO NOTHING;
        """,
                link.path,
                link.link,
                link.project_id
            )


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
            path_links.append(PathLink(path=result["path"], link=result["link"], project_id=result["project_id"]))
        return path_links
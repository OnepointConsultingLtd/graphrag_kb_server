from datetime import timezone
import datetime

from graphrag_kb_server.model.path_properties import PathProperties
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
    fetch_one,
    init_pool,
)


TB_PATH_PROPERTIES = "TB_PATH_PROPERTIES"


async def create_path_properties_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PATH_PROPERTIES} (
    ID SERIAL NOT NULL,
    PATH CHARACTER VARYING(4096) NOT NULL,
    ORIGINAL_PATH CHARACTER VARYING(4096) NULL,
    LAST_MODIFIED TIMESTAMP,
    PROJECT_ID INTEGER NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    UNIQUE (PATH, PROJECT_ID),
    CONSTRAINT PROJECT_ID
        FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID)
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_path_properties_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_PATH_PROPERTIES};
"""
    )


async def upsert_path_properties(schema_name: str, path_properties: list[PathProperties], insert_if_not_exists: bool = False):
    """Insert or update a list of PathProperties records.

    On conflict (PATH, PROJECT_ID) the LAST_MODIFIED and UPDATED_AT columns
    are refreshed so callers can safely call this repeatedly.
    """
    if not path_properties:
        return
    pool = await init_pool()
    if insert_if_not_exists and len(path_properties) > 0:
        # check first path property
        first_path_property = path_properties[0]
        count = await execute_query_with_return(
            f"""
            SELECT COUNT(*) FROM {schema_name}.{TB_PATH_PROPERTIES} WHERE PROJECT_ID = $1;
            """,
            first_path_property.project_id,
        )
        if count > 0:
            return
    async with pool.acquire() as conn:
        for props in path_properties:
            # Strip timezone info before storing: PostgreSQL TIMESTAMP (without
            # time zone) rejects aware datetimes from asyncpg.
            last_modified = props.last_modified
            if last_modified is not None and last_modified.tzinfo is not None:
                last_modified = last_modified.astimezone(timezone.utc).replace(tzinfo=None)
            await conn.execute(
                f"""
INSERT INTO {schema_name}.{TB_PATH_PROPERTIES} (PATH, ORIGINAL_PATH, LAST_MODIFIED, PROJECT_ID)
VALUES ($1, $2, $3, $4)
ON CONFLICT (PATH, PROJECT_ID) DO UPDATE
    SET ORIGINAL_PATH = EXCLUDED.ORIGINAL_PATH,
        LAST_MODIFIED = EXCLUDED.LAST_MODIFIED,
        UPDATED_AT    = now();
""",
                props.path,
                props.original_path,
                last_modified,
                props.project_id,
            )


async def find_path_properties(
    schema_name: str, path: str, project_id: int
) -> PathProperties | None:
    """Return the PathProperties for a given path and project, or None if absent."""
    row = await fetch_one(
        f"""
SELECT PATH, ORIGINAL_PATH, LAST_MODIFIED, PROJECT_ID
FROM {schema_name}.{TB_PATH_PROPERTIES}
WHERE PATH = $1 AND PROJECT_ID = $2;
""",
        path,
        project_id,
    )
    if row is None:
        return None
    last_modified = row["last_modified"]
    if last_modified is not None and last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)
    return PathProperties(
        path=row["path"],
        original_path=row["original_path"],
        project_id=row["project_id"],
        last_modified=last_modified,
    )


async def get_lastmodified_by_path(schema_name: str, path: str, project_id: int) -> datetime.datetime | None:
    found = await find_path_properties(schema_name, path, project_id)
    if found is None:
        return None
    return found.last_modified


async def find_all_path_properties(schema_name: str, project_id: int) -> list[PathProperties]:
    """Return all PathProperties records for a given project."""
    rows = await fetch_all(
        f"""
SELECT PATH, ORIGINAL_PATH, LAST_MODIFIED, PROJECT_ID
FROM {schema_name}.{TB_PATH_PROPERTIES}
WHERE PROJECT_ID = $1;
""",
        project_id,
    )
    result = []
    for row in rows:
        last_modified = row["last_modified"]
        if last_modified is not None and last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)
        result.append(
            PathProperties(
                path=row["path"],
                original_path=row["original_path"],
                project_id=row["project_id"],
                last_modified=last_modified,
            )
        )
    return result

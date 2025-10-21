from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_all
from graphrag_kb_server.model.project import Project, IndexingStatus
from graphrag_kb_server.model.engines import Engine


TB_PROJECTS = "TB_PROJECTS"


async def create_project_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PROJECTS} (
	ID SERIAL NOT NULL,
	NAME CHARACTER VARYING(100) NOT NULL,
    ENGINE CHARACTER VARYING(50) NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (NAME, ENGINE)
);
"""
    )


async def create_project(full_project: FullProject):
    schema_name = full_project.schema_name
    await create_project_table(schema_name)
    await execute_query(
        f"""
MERGE INTO {schema_name}.{TB_PROJECTS} AS t
USING (SELECT $1 AS NAME, $2 AS ENGINE) AS s
ON t.NAME = s.NAME AND t.ENGINE = s.ENGINE
WHEN MATCHED THEN
  UPDATE SET UPDATED_AT = now()
WHEN NOT MATCHED THEN
  INSERT (NAME, ENGINE, CREATED_AT, UPDATED_AT)
  VALUES (s.NAME, s.ENGINE, now(), now());
""",
        full_project.project.name,
        full_project.engine.value,
    )


async def drop_project_table(full_project: FullProject):
    schema_name = full_project.schema_name
    await execute_query(
        f"""
DELETE FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1;
""",
        full_project.project.name,
    )


async def delete_project(full_project: FullProject):
    schema_name = full_project.schema_name
    await execute_query(
        f"""
DELETE FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1;
""",
        full_project.project.name,
    )


async def project_exists(full_project: FullProject) -> bool:
    schema_name = full_project.schema_name
    result = await fetch_all(
        f"""
SELECT COUNT(*) count FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1;
""",
        full_project.project.name,
    )
    return result[0]["count"] > 0


async def find_project_by_name(schema_name: str, name: str) -> FullProject | None:
    result = await fetch_all(
        f"""
SELECT * FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1;
""",
        name,
    )
    if len(result) == 0:
        return None
    row = result[0]
    return FullProject(
        id=int(row["id"]),
        schema_name=schema_name,
        engine=Engine.GRAPHRAG,
        project=Project(
            name=row["name"],
            updated_timestamp=row["updated_at"],
            input_files=row.get("input_files", []),
            indexing_status=row.get("indexing_status", IndexingStatus.UNKNOWN),
        ),
    )

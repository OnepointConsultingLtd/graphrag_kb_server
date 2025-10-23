from pathlib import Path

from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_all
from graphrag_kb_server.model.engines import Engine, find_engine
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.model.project import SimpleProject


async def clear_table(
    schema_name: str, project_name: str, engine: Engine, table_name: str
):
    await execute_query(
        f"""
DELETE FROM {schema_name}.{table_name} WHERE PROJECT_ID = 
(SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2);
""",
        project_name,
        engine.value,
    )


def extract_elements_from_path(project_dir: Path) -> SimpleProject:
    schema_name = project_dir.parent.parent.name
    project_name = project_dir.name
    engine = project_dir.parent.name
    return SimpleProject(schema_name=schema_name, project_name=project_name, engine=find_engine(engine))


async def get_project_id(schema_name: str, project_name: str, engine: str) -> int:
    result = await fetch_all(
        f"""SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2""",
        project_name,
        engine,
    )
    if len(result) == 0:
        raise ValueError(f"Project {project_name} with engine {engine} not found")
    return result[0]["id"]


async def get_project_id_from_path(project_dir: Path) -> int:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id(
        schema_name, 
        simple_project.project_name, 
        simple_project.engine.value
    )
    return project_id

from graphrag_kb_server.service.db.db_persistence_project import (
    create_project_table,
    create_project,
)
from graphrag_kb_server.service.db.ddl_operations import create_schema
from graphrag_kb_server.model.tennant import Tennant
from graphrag_kb_server.main.project_server import project_listing
from graphrag_kb_server.model.project import FullProject
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.config import cfg


async def create_schemas_and_projects(tennants: list[Tennant]):
    for tennant in tennants:
        await create_schema(tennant.folder_name)
        await create_project_table(tennant.folder_name)
        projects = project_listing(cfg.graphrag_root_dir_path / tennant.folder_name)
        for project in projects.graphrag_projects.projects:
            await create_project(
                FullProject(
                    schema_name=tennant.folder_name,
                    engine=Engine.GRAPHRAG,
                    project=project,
                )
            )
        for project in projects.lightrag_projects.projects:
            await create_project(
                FullProject(
                    schema_name=tennant.folder_name,
                    engine=Engine.LIGHTRAG,
                    project=project,
                )
            )
        for project in projects.cag_projects.projects:
            await create_project(
                FullProject(
                    schema_name=tennant.folder_name,
                    engine=Engine.CAG,
                    project=project,
                )
            )

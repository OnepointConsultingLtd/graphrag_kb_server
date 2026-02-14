from graphrag_kb_server.service.db.db_persistence_admin_user import (
    create_admin_user_table,
    create_initial_admin_user,
)
from graphrag_kb_server.service.db.db_persistence_keywords import create_keywords_table
from graphrag_kb_server.service.db.db_persistence_links import create_links_table
from graphrag_kb_server.service.db.db_persistence_project import (
    create_project_table,
    create_project,
)
from graphrag_kb_server.service.db.db_persistence_relationships import (
    create_relationships_table,
)
from graphrag_kb_server.service.db.ddl_operations import create_schema
from graphrag_kb_server.service.db.db_persistence_topics import create_topics_table
from graphrag_kb_server.service.db.db_persistence_topics_centrality import (
    create_topics_with_centrality_table,
)
from graphrag_kb_server.model.tennant import Tennant
from graphrag_kb_server.service.project import list_projects as project_listing
from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.config import cfg
from graphrag_kb_server.service.db.connection_pool import create_connection_pool
from graphrag_kb_server.service.tennant import list_tennants
from graphrag_kb_server.service.db.db_persistence_profile import create_profile_table
from graphrag_kb_server.service.db.db_persistence_expanded_entities import (
    create_expanded_entities_table,
)
from graphrag_kb_server.service.db.db_persistence_search import (
    create_search_history_tables,
)


async def bootstrap_database():
    await create_connection_pool()
    await create_schemas_and_projects(list_tennants())


async def create_schemas_and_projects(tennants: list[Tennant]):
    for tennant in tennants:
        await create_tennant_tables(tennant)
        projects = project_listing(cfg.graphrag_root_dir_path / tennant.folder_name)
        await create_projects_and_topics(
            tennant.folder_name, projects.lightrag_projects.projects, Engine.LIGHTRAG
        )
        await create_projects_and_topics(
            tennant.folder_name, projects.cag_projects.projects, Engine.CAG
        )


async def create_tennant_tables(tennant: Tennant):
    await create_schema(tennant.folder_name)
    await create_project_table(tennant.folder_name)
    await create_profile_table(tennant.folder_name)
    await create_expanded_entities_table(tennant.folder_name)
    await create_search_history_tables(tennant.folder_name)
    await create_keywords_table(tennant.folder_name)
    await create_admin_user_table()
    await create_initial_admin_user()
    await create_relationships_table(tennant.folder_name)
    await create_links_table(tennant.folder_name)


async def create_projects_and_topics(
    schema_name: str, projects: list[Project], engine: Engine
):
    for project in projects:
        await create_project(
            FullProject(
                schema_name=schema_name,
                engine=engine,
                project=project,
            )
        )
        await create_topics_table(schema_name)
        await create_topics_with_centrality_table(schema_name)

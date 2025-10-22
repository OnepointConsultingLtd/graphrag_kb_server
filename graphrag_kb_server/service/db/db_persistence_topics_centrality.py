from pathlib import Path

from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
)
from graphrag_kb_server.model.node_centrality import NodeCentrality
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.service.db.common_operations import (
    clear_table,
    extract_elements_from_path,
    get_project_id,
)


TB_TOPICS_WITH_CENTRALITY = "TB_TOPICS_WITH_CENTRALITY"


async def create_topics_with_centrality_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_TOPICS_WITH_CENTRALITY} (
	ID SERIAL NOT NULL,
	ENTITY_ID TEXT NOT NULL,
    ENTITY_TYPE TEXT NOT NULL,
    DESCRIPTION TEXT NOT NULL,
    FILE_PATH TEXT NOT NULL,
    CENTRALITY FLOAT NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (ENTITY_ID, PROJECT_ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_topics_with_centrality(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_TOPICS_WITH_CENTRALITY};
"""
    )


async def insert_topics_with_centrality(
    project_dir: Path, node_centralities: list[NodeCentrality]
) -> int:
    schema_name, project_name, engine = extract_elements_from_path(project_dir)
    project_id = await get_project_id(schema_name, project_name, engine)
    for node_centrality in node_centralities:
        await insert_topic_with_centrality(
            schema_name, project_id, node_centrality
        )
    return len(node_centralities)


async def insert_topic_with_centrality(
    schema_name: str, project_id: int, node_centrality: NodeCentrality
) -> int:
    res = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_TOPICS_WITH_CENTRALITY} 
(ENTITY_ID, ENTITY_TYPE, DESCRIPTION, FILE_PATH, CENTRALITY, PROJECT_ID) VALUES ($1, $2, $3, $4, $5, $6)
RETURNING ID;
""",
        node_centrality[0],
        node_centrality[1],
        node_centrality[2],
        node_centrality[3],
        node_centrality[4],
        project_id,
    )
    return res


async def delete_topics_with_centrality_by_project_name(
    schema_name: str, project_name: str, engine: Engine
):
    await clear_table(schema_name, project_name, engine, TB_TOPICS_WITH_CENTRALITY)


async def find_topics_with_centrality_by_project_name(
    project_dir: Path, limit: int = -1
) -> list[NodeCentrality]:
    schema_name, project_name, engine = extract_elements_from_path(project_dir)
    limit_clause = 1000000
    if limit > 0:
        limit_clause = limit
    result = await fetch_all(
        f"""
SELECT ENTITY_ID, ENTITY_TYPE, DESCRIPTION, FILE_PATH, CENTRALITY
FROM {schema_name}.{TB_TOPICS_WITH_CENTRALITY} WHERE PROJECT_ID = 
(SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2)
AND ACTIVE = TRUE ORDER BY CENTRALITY DESC LIMIT $3;
""",
        project_name,
        engine,
        limit_clause,
    )
    return result

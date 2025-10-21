from graphrag_kb_server.service.db.connection_pool import execute_query, execute_query_with_return
from graphrag_kb_server.model.node_centrality import NodeCentrality


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


async def insert_topic_with_centrality(schema_name: str, node_centrality: NodeCentrality) -> int:
    res = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_TOPICS_WITH_CENTRALITY} 
(ENTITY_ID, ENTITY_TYPE, DESCRIPTION, FILE_PATH, CENTRALITY, PROJECT_ID) VALUES ($1, $2, $3, $4, $5, $6)
RETURNING ID;
""",
        node_centrality.entity_id,
        node_centrality.entity_type,
        node_centrality.description,
        node_centrality.file_path,
        node_centrality.centrality,
        node_centrality.project_id,
    )
    return res
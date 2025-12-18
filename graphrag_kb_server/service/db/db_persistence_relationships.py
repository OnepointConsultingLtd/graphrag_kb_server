from graphrag_kb_server.model.search.relationships import RelationshipsJSON
from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_all


TB_RELATIONSHIPS = "TB_RELATIONSHIPS"


async def create_relationships_table(schema_name: str):
    from graphrag_kb_server.service.db.db_persistence_search import TB_SEARCH_HISTORY
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_RELATIONSHIPS} (
	ID SERIAL NOT NULL,
	RELATIONSHIPS JSON NOT NULL,
    SEARCH_ID INTEGER NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
    UNIQUE (SEARCH_ID),
    CONSTRAINT SEARCH_ID
		FOREIGN KEY (SEARCH_ID) REFERENCES {schema_name}.{TB_SEARCH_HISTORY} (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_relationships_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_RELATIONSHIPS};
"""
    )


async def save_relationships(schema_name: str, relationships: RelationshipsJSON):
    await execute_query(
        f"""
INSERT INTO {schema_name}.{TB_RELATIONSHIPS} (RELATIONSHIPS, SEARCH_ID) VALUES ($1, $2)
ON CONFLICT (SEARCH_ID) DO NOTHING;
""",
        relationships.relationships,
        relationships.search_id
    )


async def find_relationships(
    schema_name: str, search_id: int
) -> RelationshipsJSON | None:
    result = await fetch_all(
        f"""
SELECT RELATIONSHIPS FROM {schema_name}.{TB_RELATIONSHIPS} WHERE SEARCH_ID = $1;
""",
        search_id,
    )
    if len(result) == 0:
        return None
    return RelationshipsJSON(
        relationships=result[0]["relationships"],
        search_id=search_id,
    )

from graphrag_kb_server.model.search.keywords import Keywords
from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_all
from graphrag_kb_server.service.db.db_persistence_search import TB_SEARCH_HISTORY


TB_KEYWORDS = "TB_KEYWORDS"


async def create_keywords_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_KEYWORDS} (
	ID SERIAL NOT NULL,
	KEYWORD VARCHAR(256) NOT NULL,
	KEYWORD_TYPE VARCHAR(4) NOT NULL,
    SEARCH_ID INTEGER NOT NULL,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (KEYWORD, SEARCH_ID),
    CONSTRAINT SEARCH_ID
		FOREIGN KEY (SEARCH_ID) REFERENCES {schema_name}.{TB_SEARCH_HISTORY} (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_keywords_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_KEYWORDS};
"""
    )


async def save_keywords(schema_name: str, keywords: Keywords):
    for keyword in keywords.keywords:
        await execute_query(
            f"""
INSERT INTO {schema_name}.{TB_KEYWORDS} (KEYWORD, KEYWORD_TYPE, SEARCH_ID) VALUES ($1, $2, $3)
ON CONFLICT (KEYWORD, SEARCH_ID) DO NOTHING;
    """,
            keyword,
            keywords.keyword_type,
            keywords.search_id,
        )


async def find_keywords(
    schema_name: str, keyword_type: str, search_id: int
) -> Keywords:
    result = await fetch_all(
        f"""
SELECT KEYWORD FROM {schema_name}.{TB_KEYWORDS} WHERE KEYWORD_TYPE = $1 AND SEARCH_ID = $2;
""",
        keyword_type,
        search_id,
    )
    return Keywords(
        keywords=[row["keyword"] for row in result],
        keyword_type=keyword_type,
        search_id=search_id,
    )

from pathlib import Path

from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
)
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.model.search.search import DocumentSearchQuery
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id_from_path,
)

TB_SEARCH_HISTORY = "TB_SEARCH_HISTORY"
TB_SEARCH_RESULTS = "TB_SEARCH_RESULTS"


async def create_search_history_tables(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_SEARCH_HISTORY} (
    ID SERIAL NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    REQUEST_ID CHARACTER VARYING(128) NOT NULL,
    LINKEDIN_PROFILE_URL TEXT NOT NULL,
    USER_ROLE CHARACTER VARYING(128) NOT NULL,
    USER_ORGANISATION_TYPE CHARACTER VARYING(128) NOT NULL,
    USER_BUSINESS_TYPE CHARACTER VARYING(128) NOT NULL,
    TOPIC_1 CHARACTER VARYING(128) NULL,
    TOPIC_2 CHARACTER VARYING(128) NULL,
    TOPIC_3 CHARACTER VARYING(128) NULL,
    BIGGEST_CHALLENGE CHARACTER VARYING(1024) NULL,
    USER_PROFILE TEXT NULL,
    RESPONSE TEXT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.{TB_PROJECTS} (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_SEARCH_RESULTS} (
    ID SERIAL NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    SEARCH_HISTORY_ID INTEGER NOT NULL,
    REQUEST_ID CHARACTER VARYING(128) NOT NULL,
    DOCUMENT_SUMMARY CHARACTER VARYING(4096) NOT NULL,
    DOCUMENT_PATH CHARACTER VARYING(1024) NOT NULL,
    DOCUMENT_MAIN_KEYWORD CHARACTER VARYING(128) NOT NULL,
    DOCUMENT_RELEVANCY_SCORE INTEGER NOT NULL,
    DOCUMENT_RELEVANCY_SCORE_REASONING CHARACTER VARYING(4096) NOT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT SEARCH_HISTORY_ID
		FOREIGN KEY (SEARCH_HISTORY_ID) REFERENCES {schema_name}.{TB_SEARCH_HISTORY} (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.{TB_PROJECTS} (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_search_history_tables(schema_name: str):
    queries = [
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_SEARCH_RESULTS};
""",
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_SEARCH_HISTORY};
""",
    ]
    for query in queries:
        await execute_query(query)


async def insert_search_query(
    project_dir: Path, document_search_query=DocumentSearchQuery
) -> int:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    user_profile = document_search_query.user_profile
    linkedin_profile_url = document_search_query.linkedin_profile_url
    user_role = document_search_query.organisation_role
    user_organisation_type = document_search_query.organisation_type
    user_business_type = document_search_query.business_type
    topics_of_interest = document_search_query.topics_of_interest
    category_entities = topics_of_interest.entity_dict.get("category")
    topic_1 = None
    topic_2 = None
    topic_3 = None
    if category_entities and category_entities.entities:
        if len(category_entities.entities) > 0:
            topic_1 = category_entities.entities[0].entity
        if len(category_entities.entities) > 1:
            topic_2 = category_entities.entities[1].entity
        if len(category_entities.entities) > 2:
            topic_3 = category_entities.entities[2].entity
    biggest_challenge = document_search_query.biggest_challenge
    search_history_id = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_SEARCH_HISTORY} 
(PROJECT_ID, REQUEST_ID, LINKEDIN_PROFILE_URL, USER_ROLE, USER_ORGANISATION_TYPE, USER_BUSINESS_TYPE, TOPIC_1, TOPIC_2, TOPIC_3, BIGGEST_CHALLENGE, USER_PROFILE)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING ID;
""",
        project_id,
        document_search_query.request_id,
        linkedin_profile_url,
        user_role,
        user_organisation_type,
        user_business_type,
        topic_1,
        topic_2,
        topic_3,
        biggest_challenge,
        user_profile,
    )
    return search_history_id


async def update_search_query_with_response(
    project_dir: Path, search_history_id: int, response: str
) -> None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    updated_count = await fetch_all(
        f"""
UPDATE {schema_name}.{TB_SEARCH_HISTORY}
SET RESPONSE = $1
WHERE ID = $2
RETURNING ID;
""",
        response,
        search_history_id,
    )
    return len(updated_count)

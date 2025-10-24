from pathlib import Path

from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
    fetch_one,
)
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
    SearchResults,
    SummarisationResponseWithDocument,
)
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id_from_path,
    DB_CACHE_EXPIRATION_TIME,
)
from graphrag_kb_server.model.digest_functions import content_sha256_combined

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
    QUERY_DIGEST_SHA256 BYTEA NOT NULL,
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
    DOCUMENT_RELEVANCY_SCORE CHARACTER VARYING(12) NOT NULL,
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
    project_dir: Path, document_search_query: DocumentSearchQuery
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
    _, query_digest_sha256 = content_sha256_combined(DocumentSearchQuery(
        request_id="",
        question=document_search_query.question,
        user_profile=document_search_query.user_profile,
        biggest_challenge=document_search_query.biggest_challenge,
        linkedin_profile_url=linkedin_profile_url,
        organisation_role=user_role,
        organisation_type=user_organisation_type,
        business_type=user_business_type,
        topics_of_interest=topics_of_interest,
    ))
    search_history_id = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_SEARCH_HISTORY} 
(PROJECT_ID, REQUEST_ID, LINKEDIN_PROFILE_URL, USER_ROLE, USER_ORGANISATION_TYPE, USER_BUSINESS_TYPE, TOPIC_1, TOPIC_2, TOPIC_3, BIGGEST_CHALLENGE, USER_PROFILE, QUERY_DIGEST_SHA256)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
        query_digest_sha256,
    )
    return search_history_id


async def process_search_response(
    project_dir: Path, search_history_id: int, search_results: SearchResults
) -> list[int]:
    await update_search_query_with_response(
        project_dir, search_history_id, search_results.response
    )
    return await insert_search_results(project_dir, search_history_id, search_results)


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


async def insert_search_results(
    project_dir: Path, search_history_id: int, search_results: SearchResults
) -> list[int]:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    search_results_ids = []
    for document in search_results.documents:
        document_summary = document.summary
        document_path = document.document_path
        document_main_keyword = document.main_keyword
        document_relevancy_score = document.relevancy_score
        document_relevancy_score_reasoning = document.relevance
        active = True
        search_results_id = await execute_query_with_return(
            f"""
INSERT INTO {schema_name}.{TB_SEARCH_RESULTS}
(PROJECT_ID, SEARCH_HISTORY_ID, REQUEST_ID, DOCUMENT_SUMMARY, DOCUMENT_PATH, DOCUMENT_MAIN_KEYWORD, DOCUMENT_RELEVANCY_SCORE, DOCUMENT_RELEVANCY_SCORE_REASONING, ACTIVE)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
RETURNING ID;
""",
            project_id,
            search_history_id,
            search_results.request_id,
            document_summary,
            document_path,
            document_main_keyword,
            document_relevancy_score.value,
            document_relevancy_score_reasoning,
            active,
        )
        search_results_ids.append(search_results_id)
    return search_results_ids


async def get_search_results(
    project_dir: Path, document_search_query: DocumentSearchQuery
) -> SearchResults | None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    _, query_digest_sha256 = content_sha256_combined(DocumentSearchQuery(
        request_id="",
        question=document_search_query.question,
        user_profile=document_search_query.user_profile,
        biggest_challenge=document_search_query.biggest_challenge,
        linkedin_profile_url=document_search_query.linkedin_profile_url,
        organisation_role=document_search_query.organisation_role,
        organisation_type=document_search_query.organisation_type,
        business_type=document_search_query.business_type,
        topics_of_interest=document_search_query.topics_of_interest,
    ))
    history_result = await fetch_one(
        f"""
SELECT ID, RESPONSE FROM {schema_name}.{TB_SEARCH_HISTORY}
WHERE PROJECT_ID = $1 AND QUERY_DIGEST_SHA256 = $2 AND ACTIVE = TRUE AND UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} day';
""",
        project_id,
        query_digest_sha256,
    )
    if history_result is None:
        return None
    search_history_id = history_result.get("id")
    response = history_result.get("response")
    search_results = await fetch_all(
        f"""
SELECT ID, DOCUMENT_SUMMARY, DOCUMENT_PATH, DOCUMENT_MAIN_KEYWORD, DOCUMENT_RELEVANCY_SCORE, DOCUMENT_RELEVANCY_SCORE_REASONING FROM {schema_name}.{TB_SEARCH_RESULTS}
WHERE SEARCH_HISTORY_ID = $1 AND ACTIVE = TRUE AND UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} day';
""",
        search_history_id,
    )
    if len(search_results) == 0:
        return None
    documents = []
    for result in search_results:
        document_summary = result.get("document_summary")
        document_path = result.get("document_path")
        document_main_keyword = result.get("document_main_keyword")
        document_relevancy_score = result.get("document_relevancy_score")
        document_relevancy_score_reasoning = result.get(
            "document_relevancy_score_reasoning"
        )
        documents.append(
            SummarisationResponseWithDocument(
                summary=document_summary,
                relevance=document_relevancy_score_reasoning,
                relevancy_score=document_relevancy_score,
                document_path=document_path,
                main_keyword=document_main_keyword,
            )
        )
    return SearchResults(
        request_id=document_search_query.request_id,
        documents=documents,
        response=response,
    )

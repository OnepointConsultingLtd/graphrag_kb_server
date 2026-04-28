from pathlib import Path
import json
from graphrag_kb_server.model.search.keywords import KeywordType
from graphrag_kb_server.model.search.relationships import RelationshipsJSON
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
    fetch_one,
)

from graphrag_kb_server.service.db.db_persistence_path_properties import TB_PATH_PROPERTIES
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
    SearchHistory,
    SearchHistoryItem,
    SearchResults,
    SummarisationResponseWithDocument,
)
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id_from_path,
    DB_CACHE_EXPIRATION_TIME,
)
from graphrag_kb_server.model.digest_functions import content_sha256_combined
from graphrag_kb_server.service.db.db_persistence_relationships import (
    find_relationships,
)
from graphrag_kb_server.utils.file_support import strip_drive

TB_SEARCH_HISTORY = "TB_SEARCH_HISTORY"
TB_SEARCH_RESULTS = "TB_SEARCH_RESULTS"


async def create_search_history_tables(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_SEARCH_HISTORY} (
    ID SERIAL NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    REQUEST_ID CHARACTER VARYING(128) NOT NULL,
    GENERATED_USER_ID CHARACTER VARYING(128) NULL,
    LINKEDIN_PROFILE_URL TEXT NOT NULL,
    USER_ROLE CHARACTER VARYING(128) NOT NULL,
    USER_ORGANISATION_TYPE CHARACTER VARYING(128) NOT NULL,
    USER_INDUSTRY CHARACTER VARYING(256) NULL,
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
    DOCUMENT_SUMMARY CHARACTER VARYING(16384) NOT NULL,
    DOCUMENT_PATH CHARACTER VARYING(16384) NOT NULL,
    DOCUMENT_MAIN_KEYWORD CHARACTER VARYING(128) NOT NULL,
    DOCUMENT_RELEVANCY_SCORE CHARACTER VARYING(12) NOT NULL,
    DOCUMENT_RELEVANCY_SCORE_REASONING CHARACTER VARYING(16384) NOT NULL,
    DOCUMENT_IMAGE CHARACTER VARYING(8192) NULL,
    DOCUMENT_LINKS TEXT[] NULL,
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
DROP TABLE IF EXISTS {schema_name}.{TB_SEARCH_HISTORY} CASCADE;
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
    user_industry = document_search_query.industry
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
    _, query_digest_sha256 = content_sha256_combined(create_search_key(document_search_query), project_dir)
    search_history_id = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_SEARCH_HISTORY} 
(PROJECT_ID, REQUEST_ID, GENERATED_USER_ID, LINKEDIN_PROFILE_URL, USER_ROLE, USER_ORGANISATION_TYPE, USER_BUSINESS_TYPE, USER_INDUSTRY, TOPIC_1, TOPIC_2, TOPIC_3, BIGGEST_CHALLENGE, USER_PROFILE, QUERY_DIGEST_SHA256)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
RETURNING ID;
""",
        project_id,
        document_search_query.request_id,
        document_search_query.generated_user_id,
        linkedin_profile_url,
        user_role,
        user_organisation_type,
        user_business_type,
        user_industry,
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


def _ensure_valid_utf8(s: str) -> str:
    """Ensure string is valid UTF-8 for database storage (replaces invalid chars)."""
    return s.encode("utf-8", errors="replace").decode("utf-8")


async def update_search_query_with_response(
    project_dir: Path, search_history_id: int, response: str
) -> None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    sanitized_response = _ensure_valid_utf8(response)
    updated_count = await fetch_all(
        f"""
UPDATE {schema_name}.{TB_SEARCH_HISTORY}
SET RESPONSE = $1
WHERE ID = $2
RETURNING ID;
""",
        sanitized_response,
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
        document_path = strip_drive(document.document_path[:16384])
        document_main_keyword = document.main_keyword
        document_relevancy_score = document.relevancy_score
        document_relevancy_score_reasoning = document.relevance
        document_image = document.image[:8192] if document.image else None
        document_links = document.links if document.links else None
        active = True
        search_results_id = await execute_query_with_return(
            f"""
INSERT INTO {schema_name}.{TB_SEARCH_RESULTS}
(PROJECT_ID, SEARCH_HISTORY_ID, REQUEST_ID, DOCUMENT_SUMMARY, DOCUMENT_PATH, DOCUMENT_MAIN_KEYWORD, 
DOCUMENT_RELEVANCY_SCORE, DOCUMENT_RELEVANCY_SCORE_REASONING, DOCUMENT_IMAGE, DOCUMENT_LINKS, ACTIVE)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
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
            document_image,
            document_links,
            active,
        )
        search_results_ids.append(search_results_id)
    return search_results_ids


def create_search_key(document_search_query: DocumentSearchQuery) -> str:
    data = {
        "linkedin_profile_url": document_search_query.linkedin_profile_url or "",
        "organisation_role": document_search_query.organisation_role or "",
        "organisation_type": document_search_query.organisation_type or "",
        "business_type": document_search_query.business_type or "",
        "industry": document_search_query.industry or "",
        "question": document_search_query.question or "",
        "biggest_challenge": document_search_query.biggest_challenge or "",
        "user_profile": document_search_query.user_profile or "",
        "topics": sorted([
            i.entity
            for v in document_search_query.topics_of_interest.entity_dict.values()
            for i in v.entities
        ]),
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


async def get_search_results(
    project_dir: Path, document_search_query: DocumentSearchQuery
) -> SearchResults | None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    search_key = create_search_key(document_search_query)
    _, query_digest_sha256 = content_sha256_combined(search_key, project_dir)
    history_result = await fetch_one(
        f"""
SELECT ID, RESPONSE FROM {schema_name}.{TB_SEARCH_HISTORY}
WHERE PROJECT_ID = $1 AND QUERY_DIGEST_SHA256 = $2 AND ACTIVE = TRUE AND UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} day' ORDER BY ID DESC;
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
SELECT R.ID, 
    R.DOCUMENT_SUMMARY, 
    R.DOCUMENT_PATH, 
    R.DOCUMENT_MAIN_KEYWORD, 
    R.DOCUMENT_RELEVANCY_SCORE, 
    R.DOCUMENT_RELEVANCY_SCORE_REASONING, 
    R.DOCUMENT_IMAGE, 
    R.DOCUMENT_LINKS,
    P.LAST_MODIFIED
FROM {schema_name}.{TB_SEARCH_RESULTS} R
    LEFT JOIN {schema_name}.{TB_PATH_PROPERTIES} P 
    ON R.DOCUMENT_PATH = P.PATH
WHERE SEARCH_HISTORY_ID = $1 AND ACTIVE = TRUE AND R.UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} days' ORDER BY DOCUMENT_RELEVANCY_SCORE DESC
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
        document_image = result.get("document_image")
        document_links = result.get("document_links") or []
        last_modified = result.get("last_modified")
        documents.append(
            SummarisationResponseWithDocument(
                summary=document_summary,
                relevance=document_relevancy_score_reasoning,
                relevancy_score=document_relevancy_score,
                document_path=document_path,
                main_keyword=document_main_keyword,
                image=document_image,
                links=document_links,
                last_modified=last_modified.isoformat() if last_modified else None,
            )
        )
    from graphrag_kb_server.service.db.db_persistence_keywords import find_keywords

    low_level_keywords = await find_keywords(
        schema_name, KeywordType.LOW_LEVEL, search_history_id
    )
    high_level_keywords = await find_keywords(
        schema_name, KeywordType.HIGH_LEVEL, search_history_id
    )
    relationships = await find_relationships(schema_name, search_history_id)
    return SearchResults(
        request_id=document_search_query.request_id,
        documents=documents,
        response=response,
        low_level_keywords=low_level_keywords,
        high_level_keywords=high_level_keywords,
        relationships=relationships,
    )


async def get_search_history(generated_user_id: str, offset: int = 0, limit: int = 10) -> SearchHistory | None:
    search_history = await fetch_all(
        f"""
select
  h.id,
  h.request_id,
  h.linkedin_profile_url,
  h.user_role,
  h.user_organisation_type,
  h.user_business_type,
  h.user_industry,
  h.topic_1,
  h.topic_2,
  h.topic_3,
  h.biggest_challenge,
  h.generated_user_id,
  h.response,
  h.created_at,
  json_agg(
    json_build_object(
      'document_summary', s.document_summary,
      'document_path', s.document_path,
      'document_main_keyword', s.document_main_keyword,
      'document_relevancy_score', s.document_relevancy_score,
      'document_relevancy_score_reasoning', s.document_relevancy_score_reasoning,
      'active', s.active,
      'created_at', s.created_at,
      'document_image', s.document_image,
      'document_links', s.document_links
    ) order by s.created_at desc
  ) as search_results,
  (select relationships from gil_fernandes.tb_relationships r where r.search_id = h.id limit 1) relationships
  from gil_fernandes.tb_search_history h
  inner join gil_fernandes.tb_search_results s on h.request_id = s.request_id
  where h.generated_user_id = $1
  group by h.id, h.request_id, h.linkedin_profile_url, h.user_role,
           h.user_organisation_type, h.user_business_type,
           h.topic_1, h.topic_2, h.topic_3,
           h.generated_user_id, h.response, h.created_at
  order by h.created_at desc
  offset $2 limit $3;
""",
        generated_user_id, offset, limit,
    )
    if len(search_history) == 0:
        return None
    results = []
    for row in search_history:
        documents = []
        search_results = json.loads(row["search_results"])
        for doc in search_results:
            documents.append(
                SummarisationResponseWithDocument(
                    summary=doc.get("document_summary", ""),
                    relevance=doc.get("document_relevancy_score_reasoning", ""),
                    relevancy_score=doc.get("document_relevancy_score", "not_relevant"),
                    document_path=doc.get("document_path", ""),
                    main_keyword=doc.get("document_main_keyword", ""),
                    image=doc.get("document_image"),
                    links=doc.get("document_links") or [],
                )
            )
        results.append(
            SearchHistoryItem(
                request_id=row["request_id"],
                linkedin_profile_url=row["linkedin_profile_url"],
                user_role=row["user_role"],
                user_organisation_type=row["user_organisation_type"],
                user_business_type=row["user_business_type"],
                user_industry=row["user_industry"],
                topic_1=row["topic_1"],
                topic_2=row["topic_2"],
                topic_3=row["topic_3"],
                biggest_challenge=row["biggest_challenge"],
                documents=documents,
                response=row["response"],
                relationships=RelationshipsJSON(relationships=row["relationships"], search_id=row["id"]),
                created_at=row["created_at"],
            )
        )
    return SearchHistory(
        results=results
    )
from pathlib import Path
import json

from pydantic.json import pydantic_encoder

from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_one
from graphrag_kb_server.service.db.common_operations import (
    get_project_id_from_path,
    extract_elements_from_path,
    DB_CACHE_EXPIRATION_TIME,
)
from graphrag_kb_server.model.digest_functions import content_sha256_combined
from graphrag_kb_server.model.search.match_query import MatchQuery, MatchOutput


TB_EXPANDED_ENTITIES = "TB_EXPANDED_ENTITIES"


async def create_expanded_entities_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_EXPANDED_ENTITIES} (
    ID SERIAL NOT NULL,
    QUESTION TEXT NOT NULL,
    LINKEDIN_PROFILE_URL TEXT NOT NULL,
    USER_PROFILE TEXT NOT NULL,
    TOPICS_OF_INTEREST JSONB NOT NULL,
    ENTITY_TYPES JSONB NOT NULL,
    ENTITIES_LIMIT INTEGER NOT NULL,
    SCORE_THRESHOLD FLOAT NOT NULL,
    PROJECT_ID INTEGER NOT NULL,
    QUERY_DIGEST_SHA256 BYTEA NOT NULL,
    MATCH_OUTPUT JSONB NOT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_expanded_entities_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_EXPANDED_ENTITIES};
"""
    )


async def insert_expanded_entities(
    project_dir: Path, match_query: MatchQuery, match_output: MatchOutput
) -> str:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    profile_dict = json.loads(match_query.user_profile)
    linkedin_profile_url = profile_dict.get("linkedin_profile_url")
    digest_sha256, query_digest_sha256 = content_sha256_combined(match_query)
    sql = f"""
MERGE INTO {schema_name}.{TB_EXPANDED_ENTITIES} AS t
USING (
  SELECT
    $1::text         AS question,
    $2::text         AS user_profile,
    $3::text         AS linkedin_profile_url,
    $4::jsonb        AS topics_of_interest,
    $5::jsonb        AS entity_types,
    $6::int          AS entities_limit,
    $7::double precision AS score_threshold,
    $8::bigint       AS project_id,
    $9::bytea        AS query_digest_sha256,
    $10::jsonb        AS match_output
) AS s
ON t.project_id = s.project_id
   AND t.query_digest_sha256 = s.query_digest_sha256
WHEN MATCHED THEN
  UPDATE SET
    match_output = s.match_output,
    updated_at   = now()
WHEN NOT MATCHED THEN
  INSERT (
    question, linkedin_profile_url, user_profile, topics_of_interest, entity_types,
    entities_limit, score_threshold, project_id, query_digest_sha256,
    match_output, created_at, updated_at
  )
  VALUES (
    s.question, s.linkedin_profile_url, s.user_profile, s.topics_of_interest, s.entity_types,
    s.entities_limit, s.score_threshold, s.project_id, s.query_digest_sha256,
    s.match_output, now(), now()
  );
"""
    await execute_query(
        sql,
        match_query.question,  # $1
        linkedin_profile_url,  # $2
        match_query.user_profile,  # $3
        json.dumps(match_query.topics_of_interest, default=pydantic_encoder),  # $4
        json.dumps(match_query.entity_types),  # $5
        match_query.entities_limit,  # $6
        match_query.score_threshold,  # $7
        project_id,  # $8
        query_digest_sha256,  # $9
        match_output.model_dump_json(),  # $10
    )
    return digest_sha256


async def get_expanded_entities(
    project_dir: Path, match_query: MatchQuery
) -> MatchOutput | None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    _, query_digest_sha256 = content_sha256_combined(match_query)
    result = await fetch_one(
        f"""
SELECT ID, MATCH_OUTPUT FROM {schema_name}.{TB_EXPANDED_ENTITIES} 
WHERE PROJECT_ID = $1 AND QUERY_DIGEST_SHA256 = $2 AND ACTIVE = TRUE AND UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} day';
""",  #
        project_id,
        query_digest_sha256,
    )
    if result is None:
        return None
    match_output = MatchOutput.model_validate_json(result.get("match_output"))
    match_output = MatchOutput(id=int(result.get("id")), **match_output.model_dump())
    return match_output


async def delete_expanded_entities(
    project_dir: Path, id: int
) -> str:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    return await execute_query(
        f"""
DELETE FROM {schema_name}.{TB_EXPANDED_ENTITIES} WHERE PROJECT_ID = $1 AND ID = $2;
""",
        project_id, id)
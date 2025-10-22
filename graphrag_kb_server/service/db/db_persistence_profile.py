from pathlib import Path
from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_one
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path, get_project_id
from graphrag_kb_server.model.linkedin.profile import Profile, Experience
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS

TB_PROFILES = "TB_PROFILES"

async def create_profile_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_PROFILES} (
	ID SERIAL NOT NULL,
	GIVEN_NAME TEXT NOT NULL,
	FAMILY_NAME TEXT NOT NULL,
    CV TEXT,
    INDUSTRY_NAME TEXT,
    GEO_LOCATION TEXT,
    LINKEDIN_PROFILE_URL TEXT NOT NULL,
    EXPERIENCES TEXT[] DEFAULT '{{}}',
    EDUCATIONS TEXT[] DEFAULT '{{}}',
    SKILLS TEXT[] DEFAULT '{{}}',
    PHOTO_200 TEXT,
    PHOTO_400 TEXT,
    PROJECT_ID INTEGER NOT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (LINKEDIN_PROFILE_URL, PROJECT_ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_profile_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_PROFILES};
"""
    )

async def insert_profile(
    project_dir: Path, profile: Profile
) -> int:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id(
        schema_name, 
        simple_project.project_name, 
        simple_project.engine.value
    )
    experiences = [experience.model_dump_json() for experience in profile.experiences]
    await execute_query(
        f"""
MERGE INTO {schema_name}.{TB_PROFILES} AS t
USING (SELECT $1 AS given_name, $2 AS surname, $3 AS cv, $4 AS industry_name, $5 AS geo_location, $6 AS linkedin_profile_url, $7::integer AS project_id, $8::text[] AS experiences) AS s
ON t.LINKEDIN_PROFILE_URL = s.LINKEDIN_PROFILE_URL AND t.PROJECT_ID = s.project_id
WHEN MATCHED THEN
  UPDATE SET CV = s.cv, INDUSTRY_NAME = s.industry_name, GEO_LOCATION = s.geo_location, EXPERIENCES = s.experiences, UPDATED_AT = now()
WHEN NOT MATCHED THEN
  INSERT (GIVEN_NAME, FAMILY_NAME, CV, INDUSTRY_NAME, GEO_LOCATION, LINKEDIN_PROFILE_URL, EXPERIENCES, PROJECT_ID, CREATED_AT, UPDATED_AT)
  VALUES (s.given_name, s.surname, s.cv, s.industry_name, s.geo_location, s.linkedin_profile_url, s.experiences, s.project_id, now(), now());
""",
        profile.given_name,
        profile.surname,
        profile.cv,
        profile.industry_name,
        profile.geo_location,
        profile.linkedin_profile_url,
        project_id,
        experiences,
    )


async def select_profile(
    project_dir: Path, linkedin_profile_url: str
) -> Profile | None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    result = await fetch_one(
        f"""
SELECT GIVEN_NAME, FAMILY_NAME, CV, INDUSTRY_NAME, GEO_LOCATION, LINKEDIN_PROFILE_URL, EXPERIENCES, PROJECT_ID, ACTIVE, CREATED_AT, UPDATED_AT
FROM {schema_name}.{TB_PROFILES} WHERE PROJECT_ID = 
(SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2)
AND ACTIVE = TRUE AND LINKEDIN_PROFILE_URL = $3 AND UPDATED_AT > now() - interval '30 day';
""",
        simple_project.project_name,
        simple_project.engine.value,
        linkedin_profile_url,
    )
    if result is None:
        return None
    experiences = [Experience.model_validate_json(experience) for experience in result.get("experiences", [])]
    return Profile(
        given_name=result.get("given_name", ""),
        surname=result.get("family_name", ""),
        email=result.get("email", ""),
        cv=result.get("cv", ""),
        industry_name=result.get("industry_name", ""),
        geo_location=result.get("geo_location", ""),
        linkedin_profile_url=result.get("linkedin_profile_url", ""),
        experiences=experiences,
    )
    
    
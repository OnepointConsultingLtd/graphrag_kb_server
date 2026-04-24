from pathlib import Path
from graphrag_kb_server.service.db.connection_pool import execute_query, fetch_one
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id_from_path,
    DB_CACHE_EXPIRATION_TIME,
)
from graphrag_kb_server.model.linkedin.profile import Education, Experience, Profile, Skill
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
    PROFILE_JSON TEXT,
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
    await execute_query(
        f"""
ALTER TABLE {schema_name}.{TB_PROFILES}
ADD COLUMN IF NOT EXISTS PROFILE_JSON TEXT;
"""
    )


async def drop_profile_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_PROFILES};
"""
    )


async def insert_profile(project_dir: Path, profile: Profile) -> int:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    project_id = await get_project_id_from_path(project_dir)
    experiences = [experience.model_dump_json() for experience in profile.experiences]
    educations = [education.model_dump_json() for education in profile.educations]
    skills = [skill.model_dump_json() for skill in profile.skills]
    profile_json = profile.profile_json or profile.model_dump_json(exclude={"profile_json"})
    await execute_query(
        f"""
MERGE INTO {schema_name}.{TB_PROFILES} AS t
USING (
  SELECT
    $1 AS given_name,
    $2 AS surname,
    $3 AS cv,
    $4 AS industry_name,
    $5 AS geo_location,
    $6 AS linkedin_profile_url,
    $7::integer AS project_id,
    $8::text[] AS experiences,
    $9::text[] AS educations,
    $10::text[] AS skills,
    $11 AS photo_200,
    $12 AS photo_400,
    $13 AS profile_json
) AS s
ON t.LINKEDIN_PROFILE_URL = s.LINKEDIN_PROFILE_URL AND t.PROJECT_ID = s.project_id
WHEN MATCHED THEN
  UPDATE SET
    CV = s.cv,
    INDUSTRY_NAME = s.industry_name,
    GEO_LOCATION = s.geo_location,
    EXPERIENCES = s.experiences,
    EDUCATIONS = s.educations,
    SKILLS = s.skills,
    PHOTO_200 = s.photo_200,
    PHOTO_400 = s.photo_400,
    PROFILE_JSON = s.profile_json,
    UPDATED_AT = now()
WHEN NOT MATCHED THEN
  INSERT (
    GIVEN_NAME, FAMILY_NAME, CV, INDUSTRY_NAME, GEO_LOCATION,
    LINKEDIN_PROFILE_URL, EXPERIENCES, EDUCATIONS, SKILLS,
    PHOTO_200, PHOTO_400, PROFILE_JSON, PROJECT_ID, CREATED_AT, UPDATED_AT
  )
  VALUES (
    s.given_name, s.surname, s.cv, s.industry_name, s.geo_location,
    s.linkedin_profile_url, s.experiences, s.educations, s.skills,
    s.photo_200, s.photo_400, s.profile_json, s.project_id, now(), now()
  );
""",
        profile.given_name,
        profile.surname,
        profile.cv,
        profile.industry_name,
        profile.geo_location,
        profile.linkedin_profile_url,
        project_id,
        experiences,
        educations,
        skills,
        profile.photo_200,
        profile.photo_400,
        profile_json,
    )


async def select_profile(
    project_dir: Path, linkedin_profile_url: str
) -> Profile | None:
    simple_project = extract_elements_from_path(project_dir)
    schema_name = simple_project.schema_name
    result = await fetch_one(
        f"""
SELECT GIVEN_NAME, FAMILY_NAME, CV, INDUSTRY_NAME, GEO_LOCATION, LINKEDIN_PROFILE_URL, EXPERIENCES, EDUCATIONS, SKILLS, PHOTO_200, PHOTO_400, PROFILE_JSON, PROJECT_ID, ACTIVE, CREATED_AT, UPDATED_AT
FROM {schema_name}.{TB_PROFILES} WHERE PROJECT_ID = 
(SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2)
AND ACTIVE = TRUE AND LINKEDIN_PROFILE_URL = $3 AND UPDATED_AT > now() - interval '{DB_CACHE_EXPIRATION_TIME} day';
""",
        simple_project.project_name,
        simple_project.engine.value,
        linkedin_profile_url,
    )
    if result is None:
        return None
    experiences = [
        Experience.model_validate_json(experience)
        for experience in result.get("experiences", [])
    ]
    educations = [
        Education.model_validate_json(education)
        for education in result.get("educations", [])
    ]
    skills = [
        Skill.model_validate_json(skill)
        for skill in result.get("skills", [])
    ]
    profile_json = result.get("profile_json")
    if profile_json:
        profile = Profile.model_validate_json(profile_json)
        return profile.model_copy(update={"profile_json": profile_json})
    return Profile(
        given_name=result.get("given_name", ""),
        surname=result.get("family_name", ""),
        email=result.get("email", ""),
        cv=result.get("cv", ""),
        industry_name=result.get("industry_name", ""),
        geo_location=result.get("geo_location", ""),
        linkedin_profile_url=result.get("linkedin_profile_url", ""),
        experiences=experiences,
        educations=educations,
        skills=skills,
        photo_200=result.get("photo_200"),
        photo_400=result.get("photo_400"),
        profile_json=profile_json,
    )

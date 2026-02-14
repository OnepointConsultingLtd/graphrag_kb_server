import pytest

from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.model.linkedin.profile import Profile
from graphrag_kb_server.test.service.db.common_test_support import create_test_project_wrapper


@pytest.mark.asyncio
async def test_create_profile():

    async def test_function(
        full_project: FullProject, _: Project, schema_name: str, project_name: str
    ):
        from graphrag_kb_server.service.db.db_persistence_profile import (
            create_profile_table,
            drop_profile_table,
            insert_profile,
            select_profile,
        )
        from graphrag_kb_server.test.service.db.common_test_support import create_project_dir
        try:
            linkedin_profile_url = "test_linkedin_profile_url"
            await create_profile_table(schema_name)
            profile = Profile(
                given_name="test_given_name",
                surname="test_surname",
                email="test_email@example.com",
                cv="test_cv",
                industry_name="test_industry_name",
                geo_location="test_geo_location",
                linkedin_profile_url=linkedin_profile_url,
                experiences=[],
            )
            fake_project_dir = create_project_dir(
                schema_name, full_project.engine, project_name
            )
            await insert_profile(fake_project_dir, profile)
            profile_data = await select_profile(fake_project_dir, linkedin_profile_url)
            assert profile_data is not None
            assert profile_data.given_name == profile.given_name
            assert profile_data.surname == profile.surname
            assert profile_data.email == ""
            assert profile_data.cv == profile.cv
            assert profile_data.industry_name == profile.industry_name
            assert profile_data.geo_location == profile.geo_location
            assert profile_data.linkedin_profile_url == profile.linkedin_profile_url
            assert profile_data.experiences == profile.experiences
        finally:
            await drop_profile_table(schema_name)

    await create_test_project_wrapper(test_function)

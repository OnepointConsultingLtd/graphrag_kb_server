from datetime import datetime

from graphrag_kb_server.model.linkedin.profile import (
    Profile,
    Experience,
    Company,
    Skill,
)
from graphrag_kb_server.test.provider.profile_provider import create_dummy_consultant


def test_profile():
    profile = Profile(
        given_name="John",
        surname="Doe",
        email="john.doe@example.com",
        cv="John Doe is a consultant with 10 years of experience in the consulting industry. He has a strong background in strategy and operations.",
        industry_name="Consulting",
        geo_location="London",
        linkedin_profile_url="https://www.linkedin.com/in/john-doe",
        experiences=[
            Experience(
                location="London",
                title="Consultant",
                start=datetime(2010, 1, 1),
                end=datetime(2020, 1, 1),
                company=Company(
                    name="Consulting",
                ),
            ),
        ],
        skills=[
            Skill(
                name="Consulting",
            ),
        ],
        photo_200="https://www.linkedin.com/in/john-doe/photo_200",
        photo_400="https://www.linkedin.com/in/john-doe/photo_400",
    )
    assert profile is not None
    assert profile.given_name == "John"
    assert profile.surname == "Doe"
    assert profile.email == "john.doe@example.com"
    assert profile.industry_name == "Consulting"
    assert profile.geo_location == "London"
    assert profile.linkedin_profile_url == "https://www.linkedin.com/in/john-doe"
    assert profile.experiences[0].location == "London"
    assert profile.experiences[0].title == "Consultant"
    assert profile.experiences[0].start == datetime(2010, 1, 1)


def test_profile_provider():
    profile = create_dummy_consultant()
    assert profile is not None
    assert profile.given_name == "John"
    assert profile.surname == "Doe"
    assert profile.email == "john.doe@example.com"
    assert profile.industry_name == "Consulting"
    assert profile.geo_location == "London"
    assert profile.linkedin_profile_url == "https://www.linkedin.com/in/john-doe"
    assert profile.experiences[0].location == "London"

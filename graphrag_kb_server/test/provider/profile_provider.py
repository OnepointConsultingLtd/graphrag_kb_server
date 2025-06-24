from datetime import datetime
from graphrag_kb_server.model.linkedin.profile import (
    Profile,
    Experience,
    Company,
    Skill,
)


def create_dummy_consultant() -> Profile:
    return Profile(
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
            )
        ],
        skills=[
            Skill(
                name="Consulting",
            ),
        ],
    )

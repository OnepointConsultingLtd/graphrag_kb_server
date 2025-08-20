import pytest
import json
from graphrag_kb_server.service.linkedin.brightdata_service import (
    scrape_linkedin_profile,
)


@pytest.mark.asyncio
async def test_scrape_linkedin_profile():
    profile_data = await scrape_linkedin_profile("gil-palma-fernandes")
    assert profile_data is not None, "Profile data is None"
    with open("gil-palma-fernandes.json", "w") as f:
        json.dump(profile_data, f)


@pytest.mark.asyncio
async def test_scrape_linkedin_profile_fail():
    profile_data = await scrape_linkedin_profile("gil-palma-fernandes-fail")
    assert profile_data is None, "Profile data is not None"

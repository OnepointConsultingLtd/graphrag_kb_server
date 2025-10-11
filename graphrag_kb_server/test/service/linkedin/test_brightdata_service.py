from pathlib import Path
import pytest
import json
from graphrag_kb_server.service.linkedin.brightdata_service import (
    scrape_linkedin_profile,
)


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
assert DATA_DIR.exists(), f"Data directory does not exist: {DATA_DIR}"
OUTPUT_DIR = DATA_DIR / "linkedin"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.asyncio
async def test_scrape_linkedin_profile():
    await download_profile_data("gil-palma-fernandes")


@pytest.mark.asyncio
async def test_scrape_linkedin_profile_allan():
    await download_profile_data("allanschweitz")


@pytest.mark.asyncio
async def test_scrape_linkedin_profile_allan():
    await download_profile_data("maithilishetty")


@pytest.mark.asyncio
async def test_scrape_linkedin_profile_fail():
    profile_data = await scrape_linkedin_profile("gil-palma-fernandes-fail")
    assert profile_data is None, "Profile data is not None"


async def download_profile_data(profile_name: str):
    profile_data = await scrape_linkedin_profile(profile_name)
    assert profile_data is not None, "Profile data for {profile_name} is None"
    with open(OUTPUT_DIR / f"{profile_name}.json", "w") as f:
        json.dump(profile_data, f)

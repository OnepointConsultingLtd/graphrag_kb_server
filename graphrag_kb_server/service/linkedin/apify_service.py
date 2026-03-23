from pathlib import Path
from apify_client import ApifyClientAsync

from graphrag_kb_server.callbacks.callback_support import BaseCallback
from graphrag_kb_server.model.linkedin.profile import Profile, Skill, Experience, Company
from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.db.db_persistence_profile import insert_profile, select_profile
from graphrag_kb_server.service.linkedin.linkedin_functions import correct_linkedin_url


LINKEDIN_ACTOR_ID = "dev_fusion/linkedin-profile-scraper"

WEBSITE_CRAWLER_ACTOR_ID = "apify/website-content-crawler"

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
POLL_INTERVAL_SECS = 5

client = ApifyClientAsync(cfg.apify_token)


def _convert_to_profile(items: list[dict], profile: str) -> Profile:
    experiences = []
    for exp in items.get("experiences", []):
        try:
            experiences.append(
                Experience(
                    location=exp.get("jobLocation", "") or "",
                    description=exp.get("jobDescription", "") or "",
                    company=Company(
                        name=exp.get("companyName", "") or ""
                    ),
                )
            )
        except Exception as e:
            logger.error(f"Error converting experience: {e}")
            continue
    return Profile(
        given_name=items.get("firstName", ""),
        surname=items.get("lastName", ""),
        email=f"{profile}@linkedin.com",
        cv=items.get("about", "") or "",
        industry_name=items.get("companyIndustry", "") or "",
        geo_location=items.get("jobLocation", "") or "",
        linkedin_profile_url=items.get("linkedinUrl", "") or "",
        skills=[Skill(name=s["title"]) for s in items.get("skills", [])],
        experiences=experiences,
    )


async def apify_crawl_website(website_url: str, callback: BaseCallback | None = None, max_crawl_pages: int = 50) -> list[dict]:
    if callback:
        await callback.callback(f"Starting crawling for {website_url}...")
    run_input = {
        "startUrls": [{"url": website_url}],
        "maxCrawlPages": max_crawl_pages,
    }
    return await apify_extract_from_url(run_input, WEBSITE_CRAWLER_ACTOR_ID, callback)


async def apify_extract_profile_items(
    profile_url: str,
    callback: BaseCallback | None = None,
) -> list[dict]:
    if callback:
        await callback.callback(f"Starting extraction for {profile_url}...")
    if not profile_url.startswith("https://www.linkedin.com/in/"):
        profile_url = f"https://www.linkedin.com/in/{profile_url}"
    run_input = {
        "profileUrls": [profile_url],
    }
    return await apify_extract_from_url(run_input, LINKEDIN_ACTOR_ID, callback)


async def apify_extract_from_url(run_input: dict, actor_id: str, callback: BaseCallback | None = None) -> list[dict]:
    run = await client.actor(actor_id).start(run_input=run_input)
    run_id = run["id"]
    status = run.get("status", "UNKNOWN")
    logger.info(f"Apify run {run_id} started with status: {status}")

    label = _extract_url_label(run_input)

    while status not in TERMINAL_STATUSES:
        if callback:
            await callback.callback(
                f"Extraction running (status: {status}) for {label}. Waiting..."
            )
        run = await client.run(run_id).wait_for_finish(wait_secs=POLL_INTERVAL_SECS)
        if run is None:
            break
        status = run.get("status", "UNKNOWN")
        logger.info(f"Apify run {run_id} status: {status}")

    if status != "SUCCEEDED":
        msg = f"Apify run {run_id} ended with status: {status}"
        logger.error(msg)
        if callback:
            await callback.callback(msg)
        return []

    if callback:
        await callback.callback(f"Extraction finished for {label}. Fetching results...")

    dataset_id = run["defaultDatasetId"]
    dataset_items = await client.dataset(dataset_id).list_items()
    return dataset_items.items


def _extract_url_label(run_input: dict) -> str:
    """Extract a human-readable URL from the run input for callback messages."""
    profile_urls = run_input.get("profileUrls")
    if profile_urls:
        return profile_urls[0]
    start_urls = run_input.get("startUrls")
    if start_urls:
        first = start_urls[0]
        return first["url"] if isinstance(first, dict) else first
    return "unknown URL"


async def apify_extract_profile(
    profile: str,
    project_dir: Path = None,
    callback: BaseCallback | None = None,
) -> Profile | None:
    if project_dir is not None:
        if profile_data := await select_profile(
            project_dir, correct_linkedin_url(profile)
        ):
            if callback is not None:
                await callback.callback("Profile already exists in database")
            return profile_data
    if callback is not None:
        await callback.callback(f"Extracting profile: {profile}. Please wait...")
    items = await apify_extract_profile_items(profile, callback=callback)
    if len(items) == 0 or items[0].get("error") is not None:
        if callback is not None:
            await callback.callback(f"Error extracting profile: {profile}: {items[0].get("error")}")
        return None
    profile_content = _convert_to_profile(items[0], profile)
    if project_dir is not None and profile_content is not None:
        await insert_profile(project_dir, profile_content)
    if callback is not None:
        await callback.callback(f"Profile extracted successfully: {profile}")
    return profile_content


if __name__ == "__main__":
    import json
    import asyncio

    def write_to_file(items: list[dict], file_name: str):
        with open(file_name, "w") as f:
            json.dump(items, f, indent=4)

    def write_to_file_profile(profile: Profile, file_name: str):
        with open(file_name, "w") as f:
            json.dump(profile.model_dump(), f, indent=4)

    def extract_profiles():
        profiles = [
            "gil-palma-fernandes",
            "chrisjwray",
            "rajoojha",
            "leshinesbusinessperformancexec",
            "susan-challenger-a-isp-07585073",
            "jennie-harnaman-8b1a4019",
            "alexandru-daniel-tufa-4a9280106"
        ]

        async def apify_extract_profile_to_file():
            for profile in profiles:
                profile_content = await apify_extract_profile(profile)
                write_to_file_profile(
                    profile_content, f"data/{profile}_profile.json"
                )

        asyncio.run(apify_extract_profile_to_file())

    async def extract_onepoint():
        website_url = "https://www.onepointltd.com/"
        write_to_file(
            await apify_crawl_website(website_url,  max_crawl_pages=20), f"data/onepoint_raw.json"
        )

    asyncio.run(extract_onepoint())

    

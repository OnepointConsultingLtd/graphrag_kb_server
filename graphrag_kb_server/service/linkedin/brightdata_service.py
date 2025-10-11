import asyncio
import httpx
import time

from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.linkedin.linkedin_functions import correct_linkedin_url
from graphrag_kb_server.config import bright_data_cfg

from graphrag_kb_server.utils.cache import GenericSimpleCache

_cache = GenericSimpleCache[str, dict](timeout=60 * 60 * 4)  # 4 hours


API_BASE_URL = "https://api.brightdata.com"
API_KEY = bright_data_cfg.bright_data_api_key
LINKEDIN_ENDPOINT = f"{API_BASE_URL}/datasets/v3/trigger?dataset_id=gd_l1viktl72bvl7bjuj0&include_errors=true"


_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}


async def _poll_progress(
    snapshot_id: str,
    client: httpx.AsyncClient,
    poll_interval: int = 5,
    timeout: int = 300,
) -> bool:
    start = time.time()
    status = "running"
    while time.time() - start < timeout:
        pr = await client.get(
            f"{API_BASE_URL}/datasets/v3/progress/{snapshot_id}", headers=_headers
        )
        if pr.status_code != 200:
            logger.error(f"Error polling progress: {pr.status_code}")
            logger.error(pr.text)
            return False
        status = pr.json().get("status", "unknown")
        if status in {"ready", "completed"}:
            return True
        if status in {"failed", "error"}:
            logger.error(f"Snapshot failed: {pr.text}")
            return False
        await asyncio.sleep(poll_interval)
    return False


async def scrape_linkedin_profile(
    url: str, poll_interval: int = 5, timeout: int = 300
) -> dict | None:
    if cached_result := _cache.get(url):
        return cached_result
    url = correct_linkedin_url(url)
    payload = [{"url": url}]
    async with httpx.AsyncClient() as client:
        response = await client.post(LINKEDIN_ENDPOINT, json=payload, headers=_headers)
        data = response.json()
        if response.status_code == 200:
            snapshot_id = data.get("snapshot_id")
            if not snapshot_id:
                logger.error(f"No snapshot_id found in response: {data}")
                return None
            if await _poll_progress(snapshot_id, client, poll_interval, timeout):
                snapshot_url = f"{API_BASE_URL}/datasets/v3/snapshot/{snapshot_id}"
                snapshot_response = await client.get(snapshot_url, headers=_headers)
                snapshot_data = snapshot_response.json()
                warning_code = snapshot_data.get("warning_code")
                if warning_code == "dead_page":
                    logger.error(f"Dead page: {snapshot_data}")
                    return None
                _cache.set(url, snapshot_data)
                return snapshot_data
            else:
                logger.error(f"Snapshot failed: {snapshot_id}")
                return None
        else:
            logger.error(f"Error scraping LinkedIn profile: {response.status_code}")
            logger.error(data)
            return None

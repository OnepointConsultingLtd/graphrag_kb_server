import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.db.common_operations import get_project_id
from graphrag_kb_server.service.db.connection_pool import close_connection_pool
from graphrag_kb_server.service.db.db_persistence_links import (
    create_path_links_table,
    extract_vimeo_id,
    replace_website_path_links,
)
from graphrag_kb_server.service.lightrag.lightrag_constants import (
    INPUT_FOLDER,
    LIGHTRAG_FOLDER,
)
from graphrag_kb_server.service.lightrag.lightrag_index_support import lightrag_index
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.link_extraction_service import save_links

CLUSTRE_VIDEOS_URL = "https://www.clustre.net/category/videos/"
USER_AGENT = "Mozilla/5.0 (compatible; graphrag-kb-server/1.0)"
REQUEST_TIMEOUT = 30

VIMEO_PLAYER_PATTERN = re.compile(r"player\.vimeo\.com/video/(\d+)")

VIMEO_API_URL = "https://api.vimeo.com"
VIMEO_API_ACCEPT = "application/vnd.vimeo.*+json;version=3.4"
WEBSITE_VIDEOS_FOLDER = "website_videos"
VTT_TIMESTAMP_PATTERN = re.compile(r"-->")
VTT_TAG_PATTERN = re.compile(r"<[^>]+>")


def extract_article_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for item in soup.select("div.item-grid"):
        anchor = item.find("a", href=True)
        if anchor is None:
            continue
        url = urljoin(page_url, anchor["href"].strip())
        if url not in urls:
            urls.append(url)
    return urls


def extract_next_page_url(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.find("link", rel="next", href=True) or soup.find(
        "a", class_="emm-next", href=True
    )
    if next_link is None:
        return None
    return urljoin(page_url, next_link["href"].strip())


def extract_vimeo_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for iframe in soup.find_all("iframe", src=True):
        match = VIMEO_PLAYER_PATTERN.search(iframe["src"])
        if match is None:
            continue
        link = f"https://vimeo.com/{match.group(1)}"
        if link not in links:
            links.append(link)
    return links


async def _fetch(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    return response.text


async def collect_article_urls(client: httpx.AsyncClient, start_url: str) -> list[str]:
    article_urls: list[str] = []
    visited_pages: set[str] = set()
    page_url: str | None = start_url
    while page_url is not None and page_url not in visited_pages:
        visited_pages.add(page_url)
        html = await _fetch(client, page_url)
        for url in extract_article_urls(html, page_url):
            if url not in article_urls:
                article_urls.append(url)
        page_url = extract_next_page_url(html, page_url)
    return article_urls


async def parse_vimeo_mapping(
    start_url: str = CLUSTRE_VIDEOS_URL,
) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        article_urls = await collect_article_urls(client, start_url)
        logger.info(f"Found {len(article_urls)} articles in {start_url}")
        for article_url in article_urls:
            try:
                vimeo_links = extract_vimeo_links(await _fetch(client, article_url))
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch {article_url}: {e}")
                continue
            if vimeo_links:
                mapping[article_url] = vimeo_links
    return mapping


def vtt_to_text(vtt: str) -> str:
    lines: list[str] = []
    for raw_line in vtt.splitlines():
        line = VTT_TAG_PATTERN.sub("", raw_line).strip()
        if (
            not line
            or line.startswith("WEBVTT")
            or line.isdigit()
            or VTT_TIMESTAMP_PATTERN.search(line)
        ):
            continue
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return "\n".join(lines)


def _select_text_track(tracks: list[dict]) -> dict | None:
    if not tracks:
        return None
    return sorted(
        tracks,
        key=lambda track: (
            not (track.get("language") or "").startswith("en"),
            not track.get("active", False),
        ),
    )[0]


async def fetch_transcript(
    client: httpx.AsyncClient, vimeo_id: str, token: str
) -> str | None:
    try:
        response = await client.get(
            f"{VIMEO_API_URL}/videos/{vimeo_id}/texttracks",
            headers={"Authorization": f"bearer {token}", "Accept": VIMEO_API_ACCEPT},
        )
        response.raise_for_status()
        track = _select_text_track(response.json().get("data", []))
        if track is None or not track.get("link"):
            logger.info(f"No text tracks for Vimeo video {vimeo_id}")
            return None
        # The track link is a pre-signed URL and must be fetched without the API token
        vtt = await _fetch(client, track["link"])
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch text tracks for Vimeo video {vimeo_id}: {e}")
        return None
    transcript = vtt_to_text(vtt)
    return transcript or None


def transcript_file_name(article_url: str, vimeo_id: str) -> str:
    segments = [s for s in urlparse(article_url).path.split("/") if s]
    slug = segments[-1] if segments else "video"
    return f"{slug}_{vimeo_id}.txt"


def transcript_content(article_url: str, vimeo_id: str, transcript: str) -> str:
    return (
        f"Video: https://vimeo.com/{vimeo_id}\n"
        f"Web page: {article_url}\n\n"
        f"{transcript}\n"
    )


async def write_transcripts(
    videos_folder: Path, missing: dict[str, list[str]], token: str
) -> list[Path]:
    videos_folder.mkdir(parents=True, exist_ok=True)
    transcript_files: list[Path] = []
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        for article_url, vimeo_links in missing.items():
            for vimeo_link in vimeo_links:
                vimeo_id = extract_vimeo_id(vimeo_link)
                if vimeo_id is None:
                    continue
                file = videos_folder / transcript_file_name(article_url, vimeo_id)
                if not file.exists():
                    transcript = await fetch_transcript(client, vimeo_id, token)
                    if transcript is None:
                        continue
                    file.write_text(
                        transcript_content(article_url, vimeo_id, transcript),
                        encoding="utf-8",
                    )
                    logger.info(f"Wrote transcript {file}")
                if file not in transcript_files:
                    transcript_files.append(file)
    return transcript_files


def _log_missing(missing: dict[str, list[str]], reason: str):
    for article_url, vimeo_links in missing.items():
        for vimeo_link in vimeo_links:
            logger.warning(f"{reason}: {article_url} -> {vimeo_link}")


async def sync_clustre_videos(schema_name: str, project_name: str, engine: str):
    from graphrag_kb_server.service.project import write_project_file

    await create_path_links_table(schema_name)
    project_id = await get_project_id(schema_name, project_name, engine)
    mapping = await parse_vimeo_mapping()
    if not mapping:
        logger.warning("No Vimeo links found, keeping existing links")
        return
    missing = await replace_website_path_links(schema_name, project_id, mapping)
    logger.info(
        f"Updated website links for {len(mapping)} pages, {len(missing)} pages have videos not in {schema_name}.{project_name}"
    )
    if not missing:
        return
    token = cfg.vimeo_personal_access_token
    if not token:
        _log_missing(missing, "No VIMEO_PERSONAL_ACCESS_TOKEN, not indexed")
        return
    if engine != LIGHTRAG_FOLDER:
        _log_missing(missing, f"Engine {engine} is not supported, not indexed")
        return
    project_dir = cfg.graphrag_root_dir_path / schema_name / engine / project_name
    if not project_dir.exists():
        _log_missing(missing, f"Project folder {project_dir} not found, not indexed")
        return
    transcript_files = await write_transcripts(
        project_dir / INPUT_FOLDER / WEBSITE_VIDEOS_FOLDER, missing, token
    )
    if transcript_files:
        write_project_file(project_dir, IndexingStatus.IN_PROGRESS)
        try:
            rag = await initialize_rag(project_dir)
            await lightrag_index(rag, transcript_files)
            await save_links(project_dir, files=transcript_files)
            write_project_file(project_dir, IndexingStatus.COMPLETED)
        except Exception:
            write_project_file(project_dir, IndexingStatus.FAILED)
            raise
    still_missing = await replace_website_path_links(schema_name, project_id, mapping)
    _log_missing(still_missing, "Video still not in path links")


def _target_project() -> tuple[str, str, str]:
    return (
        os.getenv("CLUSTRE_VIMEO_SCHEMA", "gil_fernandes"),
        os.getenv("CLUSTRE_VIMEO_PROJECT", "clustre_full_5"),
        os.getenv("CLUSTRE_VIMEO_ENGINE", "lightrag"),
    )


async def run_clustre_vimeo_sync_loop():
    while True:
        try:
            await sync_clustre_videos(*_target_project())
        except Exception as e:
            logger.error(f"Clustre Vimeo sync failed: {e}")
            logger.exception(e)
        await asyncio.sleep(cfg.clustre_vimeo_sync_interval_hours * 3600)


async def main():
    try:
        await sync_clustre_videos(*_target_project())
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())

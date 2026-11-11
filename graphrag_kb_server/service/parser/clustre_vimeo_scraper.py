import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import init_logger, logger
from graphrag_kb_server.service.db.common_operations import get_project_id
from graphrag_kb_server.service.db.connection_pool import close_connection_pool
from graphrag_kb_server.service.db.db_persistence_links import (
    create_path_links_table,
    extract_vimeo_id,
    replace_website_path_links,
)
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.parser.clustre_scraper_common import (  # noqa: F401 - re-exported for existing callers
    PAGE_CONTENT_SELECTOR,
    PAGE_NOISE_SELECTORS,
    PAGE_TEXT_TAGS,
    REQUEST_TIMEOUT,
    USER_AGENT,
    collect_article_urls,
    create_http_client,
    extract_article_urls,
    extract_next_page_url,
    extract_page_text,
    extract_page_title,
    fetch_html,
    format_progress,
    index_files_into_project,
    resolve_lightrag_project_dir,
    run_periodic_sync,
)
from graphrag_kb_server.service.parser.vimeo_audio_transcription import (
    transcribe_vimeo_audio,
)

CLUSTRE_VIDEOS_URL = os.getenv("CLUSTRE_VIDEOS_URL", "https://www.clustre.net/category/videos/")
VIMEO_PLAYER_PATTERN = re.compile(r"player\.vimeo\.com/video/(\d+)")

VIMEO_API_URL = "https://api.vimeo.com"
VIMEO_API_ACCEPT = "application/vnd.vimeo.*+json;version=3.4"
WEBSITE_VIDEOS_FOLDER = "website_videos"
VTT_TIMESTAMP_PATTERN = re.compile(r"-->")
VTT_TAG_PATTERN = re.compile(r"<[^>]+>")

PAGE_TEXT_SECTION_TITLE = "Page text"
TRANSCRIPT_SECTION_TITLE = "Video transcript"


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


async def parse_vimeo_mapping(
    start_url: str = CLUSTRE_VIDEOS_URL,
) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    async with create_http_client() as client:
        article_urls = await collect_article_urls(client, start_url)
        logger.info(f"Found {len(article_urls)} articles in {start_url}")
        for article_url in article_urls:
            try:
                logger.info(f"Extracting clustre url: {article_url}")
                vimeo_links = extract_vimeo_links(await fetch_html(client, article_url))
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch {article_url}: {e}")
                continue
            if vimeo_links:
                for link in vimeo_links:
                    logger.info(f"Clustre vimeo link: {article_url}: {link}")
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
        vtt = await fetch_html(client, track["link"])
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch text tracks for Vimeo video {vimeo_id}: {e}")
        return None
    transcript = vtt_to_text(vtt)
    return transcript or None


def transcript_file_name(article_url: str, vimeo_id: str) -> str:
    segments = [s for s in urlparse(article_url).path.split("/") if s]
    slug = segments[-1] if segments else "video"
    return f"{slug}_{vimeo_id}.txt"


def transcript_content(
    article_url: str, vimeo_id: str, transcript: str, page_text: str = ""
) -> str:
    """Build the file content to index: video and page links, page text and video transcript.

    The page text section is left out when the page has no extractable text.
    """
    header = f"Video: https://vimeo.com/{vimeo_id}\nWeb page: {article_url}\n\n"
    if not page_text:
        return f"{header}{transcript}\n"
    return (
        f"{header}"
        f"## {PAGE_TEXT_SECTION_TITLE}\n\n{page_text}\n\n"
        f"## {TRANSCRIPT_SECTION_TITLE}\n\n{transcript}\n"
    )


async def fetch_page_text(client: httpx.AsyncClient, article_url: str) -> str:
    """Fetch an article and extract its text, returning an empty text if that fails."""
    try:
        return extract_page_text(await fetch_html(client, article_url))
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch page text of {article_url}: {e}")
        return ""


async def fetch_transcript_with_audio_fallback(
    client: httpx.AsyncClient, vimeo_id: str, article_url: str, token: str
) -> str | None:
    """Fetch the Vimeo text track and fall back to speech to text on the audio."""
    transcript = await fetch_transcript(client, vimeo_id, token)
    if transcript is not None:
        return transcript
    logger.info(f"Falling back to audio transcription for Vimeo video {vimeo_id}")
    return await transcribe_vimeo_audio(vimeo_id, article_url, token=token)


async def write_transcripts(
    videos_folder: Path, missing: dict[str, list[str]], token: str
) -> list[Path]:
    videos_folder.mkdir(parents=True, exist_ok=True)
    transcript_files: list[Path] = []
    # A page can embed several videos, so its text is fetched only once
    page_texts: dict[str, str] = {}
    async with create_http_client() as client:
        total_videos = sum(len(vimeo_links) for vimeo_links in missing.values())
        video_position = 0
        for article_url, vimeo_links in missing.items():
            for vimeo_link in vimeo_links:
                video_position += 1
                progress = format_progress(video_position, total_videos)
                vimeo_id = extract_vimeo_id(vimeo_link)
                if vimeo_id is None:
                    logger.warning(f"{progress} No Vimeo id in {vimeo_link}, skipped")
                    continue
                file = videos_folder / transcript_file_name(article_url, vimeo_id)
                if file.exists():
                    logger.info(f"{progress} Transcript already exists: {file.name}")
                else:
                    logger.info(
                        f"{progress} Transcribing Vimeo video {vimeo_id} of {article_url}"
                    )
                    transcript = await fetch_transcript_with_audio_fallback(
                        client, vimeo_id, article_url, token
                    )
                    if transcript is None:
                        logger.warning(
                            f"{progress} No transcript for Vimeo video {vimeo_id}, skipped"
                        )
                        continue
                    if article_url not in page_texts:
                        page_texts[article_url] = await fetch_page_text(
                            client, article_url
                        )
                    file.write_text(
                        transcript_content(
                            article_url,
                            vimeo_id,
                            transcript,
                            page_texts[article_url],
                        ),
                        encoding="utf-8",
                    )
                    logger.info(f"{progress} Wrote transcript {file}")
                if file not in transcript_files:
                    transcript_files.append(file)
    return transcript_files


def _log_missing(missing: dict[str, list[str]], reason: str):
    for article_url, vimeo_links in missing.items():
        for vimeo_link in vimeo_links:
            logger.warning(f"{reason}: {article_url} -> {vimeo_link}")


async def sync_clustre_videos(schema_name: str, project_name: str, engine: str):
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
    project_dir = resolve_lightrag_project_dir(schema_name, project_name, engine)
    if project_dir is None:
        _log_missing(missing, "Project cannot be indexed, video not indexed")
        return
    transcript_files = await write_transcripts(
        project_dir / INPUT_FOLDER / WEBSITE_VIDEOS_FOLDER, missing, token
    )
    await index_files_into_project(project_dir, transcript_files)
    still_missing = await replace_website_path_links(schema_name, project_id, mapping)
    _log_missing(still_missing, "Video still not in path links")


def _target_project() -> tuple[str, str, str]:
    return (
        os.getenv("CLUSTRE_VIMEO_SCHEMA", "gil_fernandes"),
        os.getenv("CLUSTRE_VIMEO_PROJECT", "clustre_full_5"),
        os.getenv("CLUSTRE_VIMEO_ENGINE", "lightrag"),
    )


async def run_clustre_vimeo_sync_loop():
    """Sync the Clustre videos forever, every CLUSTRE_VIMEO_SYNC_INTERVAL_HOURS hours."""
    await run_periodic_sync(
        lambda: sync_clustre_videos(*_target_project()),
        cfg.clustre_vimeo_sync_interval_hours,
        "Clustre Vimeo",
    )


async def main():
    # Imports above (lightrag) reset the logging configuration, so restore it
    init_logger()
    try:
        await sync_clustre_videos(*_target_project())
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())

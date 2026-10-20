import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import init_logger, logger
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
from graphrag_kb_server.service.parser.vimeo_audio_transcription import (
    transcribe_vimeo_audio,
)

CLUSTRE_VIDEOS_URL = os.getenv("CLUSTRE_VIDEOS_URL", "https://www.clustre.net/category/videos/")
USER_AGENT = "Mozilla/5.0 (compatible; graphrag-kb-server/1.0)"
REQUEST_TIMEOUT = 30

VIMEO_PLAYER_PATTERN = re.compile(r"player\.vimeo\.com/video/(\d+)")

VIMEO_API_URL = "https://api.vimeo.com"
VIMEO_API_ACCEPT = "application/vnd.vimeo.*+json;version=3.4"
WEBSITE_VIDEOS_FOLDER = "website_videos"
VTT_TIMESTAMP_PATTERN = re.compile(r"-->")
VTT_TAG_PATTERN = re.compile(r"<[^>]+>")

PAGE_CONTENT_SELECTOR = "#internalContent"
PAGE_NOISE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "form",
    "nav",
    "header",
    "footer",
    ".footerStyle",
    "#inlinePopUp",
    "#cookie-notice",
]
PAGE_TEXT_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"]
PAGE_TEXT_SECTION_TITLE = "Page text"
TRANSCRIPT_SECTION_TITLE = "Video transcript"


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
                logger.info(f"Extracting clustre url: {article_url}")
                vimeo_links = extract_vimeo_links(await _fetch(client, article_url))
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


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_page_title(soup: BeautifulSoup) -> str:
    """Return the headline of the article, falling back to the html title without the site name."""
    heading = soup.find("h1")
    if heading is not None and heading.get_text(strip=True):
        return _normalize_whitespace(heading.get_text(" "))
    if soup.title is not None and soup.title.string:
        return _normalize_whitespace(soup.title.string.split("|")[0])
    return ""


def extract_page_text(html: str) -> str:
    """Extract the readable article text of a Clustre page, without menus, footer or popups.

    The article body is the element PAGE_CONTENT_SELECTOR. For pages without it, the
    whole body is used after removing the elements listed in PAGE_NOISE_SELECTORS.
    The text is returned as the title followed by one paragraph per line.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = extract_page_title(soup)
    container = soup.select_one(PAGE_CONTENT_SELECTOR) or soup.body or soup
    for noise in container.select(", ".join(PAGE_NOISE_SELECTORS)):
        noise.decompose()
    # Only leaf blocks are used, otherwise the text of a list item containing a paragraph is doubled
    paragraphs = [
        _normalize_whitespace(block.get_text(" "))
        for block in container.find_all(PAGE_TEXT_TAGS)
        if block.find(PAGE_TEXT_TAGS) is None
    ]
    if not any(paragraphs):
        paragraphs = [
            _normalize_whitespace(line) for line in container.get_text("\n").split("\n")
        ]
    lines = [title] if title else []
    for paragraph in paragraphs:
        if paragraph and (not lines or lines[-1] != paragraph):
            lines.append(paragraph)
    return "\n".join(lines)


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
        return extract_page_text(await _fetch(client, article_url))
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


def format_progress(position: int, total: int) -> str:
    """Format the position of an item in a batch for log messages, e.g. '[3/120]'."""
    return f"[{position}/{total}]"


async def write_transcripts(
    videos_folder: Path, missing: dict[str, list[str]], token: str
) -> list[Path]:
    videos_folder.mkdir(parents=True, exist_ok=True)
    transcript_files: list[Path] = []
    # A page can embed several videos, so its text is fetched only once
    page_texts: dict[str, str] = {}
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
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
    # Imports above (lightrag) reset the logging configuration, so restore it
    init_logger()
    try:
        await sync_clustre_videos(*_target_project())
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())

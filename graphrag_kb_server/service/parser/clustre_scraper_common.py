"""Building blocks shared by the Clustre website scrapers (videos and articles).

Both scrapers crawl the paginated category listings of https://www.clustre.net,
extract the readable text of the pages and index new documents into a LightRAG
project. The pieces they have in common live here so that they are not duplicated.
"""

import asyncio
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.indexing_job_registry import indexing_job_registry
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_index_support import lightrag_index
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.link_extraction_service import save_links

USER_AGENT = "Mozilla/5.0 (compatible; graphrag-kb-server/1.0)"
REQUEST_TIMEOUT = 30

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
    ".social-sharing",
]
PAGE_TEXT_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"]
PLAIN_TEXT_TAG = "text"
SECONDS_PER_HOUR = 3600


def create_http_client() -> httpx.AsyncClient:
    """Create the HTTP client used to crawl the Clustre website.

    It identifies itself with USER_AGENT, uses REQUEST_TIMEOUT and follows redirects.
    """
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    )


async def fetch_html(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a page and return its body, raising httpx.HTTPError on failure."""
    response = await client.get(url)
    response.raise_for_status()
    return response.text


def extract_article_urls(html: str, page_url: str) -> list[str]:
    """Return the URLs of the entries (div.item-grid) of a category listing page, in order and without duplicates."""
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
    """Return the URL of the next listing page, or None on the last page."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.find("link", rel="next", href=True) or soup.find(
        "a", class_="emm-next", href=True
    )
    if next_link is None:
        return None
    return urljoin(page_url, next_link["href"].strip())


async def collect_article_urls(client: httpx.AsyncClient, start_url: str) -> list[str]:
    """Follow the pagination of a category listing and return the URLs of all its entries."""
    article_urls: list[str] = []
    visited_pages: set[str] = set()
    page_url: str | None = start_url
    while page_url is not None and page_url not in visited_pages:
        visited_pages.add(page_url)
        html = await fetch_html(client, page_url)
        for url in extract_article_urls(html, page_url):
            if url not in article_urls:
                article_urls.append(url)
        page_url = extract_next_page_url(html, page_url)
    return article_urls


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs into single spaces and strip the ends."""
    return " ".join(text.split())


def extract_page_title(soup: BeautifulSoup) -> str:
    """Return the headline of the article, falling back to the html title without the site name."""
    heading = soup.find("h1")
    if heading is not None and heading.get_text(strip=True):
        return _normalize_whitespace(heading.get_text(" "))
    if soup.title is not None and soup.title.string:
        return _normalize_whitespace(soup.title.string.split("|")[0])
    return ""


def extract_content_blocks(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extract the readable blocks of a Clustre page, without menus, footer, popups or share buttons.

    The article body is the element PAGE_CONTENT_SELECTOR. For pages without it, the
    whole body is used after removing the elements listed in PAGE_NOISE_SELECTORS.
    The soup is modified, as the noise elements are removed from it.

    Returns:
        (tag_name, text) pairs of the leaf text blocks in document order. When the
        page has no text blocks, its plain text lines are returned with the tag
        PLAIN_TEXT_TAG. Empty blocks are left out.
    """
    container = soup.select_one(PAGE_CONTENT_SELECTOR) or soup.body or soup
    for noise in container.select(", ".join(PAGE_NOISE_SELECTORS)):
        noise.decompose()
    # Only leaf blocks are used, otherwise the text of a list item containing a paragraph is doubled
    blocks = [
        (block.name, _normalize_whitespace(block.get_text(" ")))
        for block in container.find_all(PAGE_TEXT_TAGS)
        if block.find(PAGE_TEXT_TAGS) is None
    ]
    if not any(text for _, text in blocks):
        blocks = [
            (PLAIN_TEXT_TAG, _normalize_whitespace(line))
            for line in container.get_text("\n").split("\n")
        ]
    return [(tag_name, text) for tag_name, text in blocks if text]


def extract_page_text(html: str) -> str:
    """Extract the readable article text of a Clustre page, without menus, footer or popups.

    The text is returned as the title followed by one paragraph per line, with
    consecutive duplicate lines removed.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = extract_page_title(soup)
    lines = [title] if title else []
    for _, paragraph in extract_content_blocks(soup):
        if not lines or lines[-1] != paragraph:
            lines.append(paragraph)
    return "\n".join(lines)


def format_progress(position: int, total: int) -> str:
    """Format the position of an item in a batch for log messages, e.g. '[3/120]'."""
    return f"[{position}/{total}]"


def resolve_lightrag_project_dir(
    schema_name: str, project_name: str, engine: str
) -> Path | None:
    """Return the folder of a LightRAG project into which documents can be indexed.

    Returns:
        The project folder, or None (with the reason logged) when the engine is
        not LightRAG or the folder does not exist.
    """
    if engine != LIGHTRAG_FOLDER:
        logger.warning(f"Engine {engine} is not supported, nothing indexed")
        return None
    project_dir = cfg.graphrag_root_dir_path / schema_name / engine / project_name
    if not project_dir.exists():
        logger.warning(f"Project folder {project_dir} not found, nothing indexed")
        return None
    return project_dir


async def index_files_into_project(project_dir: Path, files: list[Path]):
    """Insert files into the LightRAG index of a project and save the links they contain.

    The project lock of the indexing job registry is held while indexing, so that
    the scheduled syncs and user uploads never modify the same index concurrently.
    The project status is IN_PROGRESS while indexing, then COMPLETED, or FAILED
    if indexing raises (the error is re-raised).
    """
    from graphrag_kb_server.service.project import write_project_file

    if not files:
        return
    async with indexing_job_registry.project_lock(project_dir):
        write_project_file(project_dir, IndexingStatus.IN_PROGRESS)
        try:
            rag = await initialize_rag(project_dir)
            await lightrag_index(rag, files)
            await save_links(project_dir, files=files)
            write_project_file(project_dir, IndexingStatus.COMPLETED)
        except Exception:
            write_project_file(project_dir, IndexingStatus.FAILED)
            raise


async def run_periodic_sync(
    sync_coroutine_factory: Callable[[], Awaitable[None]],
    interval_hours: float,
    label: str,
):
    """Run a sync forever, waiting interval_hours between runs.

    A failing run is logged and does not stop the loop. The loop ends only when
    its task is cancelled.
    """
    while True:
        try:
            await sync_coroutine_factory()
        except Exception as e:
            logger.error(f"{label} sync failed: {e}")
            logger.exception(e)
        await asyncio.sleep(interval_hours * SECONDS_PER_HOUR)

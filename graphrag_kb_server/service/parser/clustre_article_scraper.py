"""Keeps a LightRAG project up to date with the articles of the Clustre website.

The article listing at CLUSTRE_ARTICLES_URL is crawled, every article which is
not yet linked in the project (TB_PATH_LINKS) is converted to a markdown document
that contains its source URL, and the new documents are indexed with LightRAG.
"""

import argparse
import asyncio
import os
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
    find_path_links,
)
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.parser.clustre_scraper_common import (
    collect_article_urls,
    create_http_client,
    extract_content_blocks,
    extract_page_title,
    fetch_html,
    format_progress,
    index_files_into_project,
    resolve_lightrag_project_dir,
    run_periodic_sync,
)

CLUSTRE_ARTICLES_URL = os.getenv(
    "CLUSTRE_ARTICLES_URL", "https://www.clustre.net/category/articles/"
)
WEBSITE_ARTICLES_FOLDER = "website_articles"
SOURCE_LABEL = "Source"
PUBLISHED_LABEL = "Published"
PUBLISHED_TIME_PROPERTY = "article:published_time"
ISO_DATE_LENGTH = len("YYYY-MM-DD")
ARTICLE_FILE_EXTENSION = ".md"
DEFAULT_ARTICLE_SLUG = "article"
WWW_PREFIX = "www."

SUBHEADING_PREFIXES = {
    "h1": "##",
    "h2": "##",
    "h3": "###",
    "h4": "###",
    "h5": "###",
    "h6": "###",
}
LIST_ITEM_TAG = "li"
BLOCKQUOTE_TAG = "blockquote"


def extract_published_date(soup: BeautifulSoup) -> str | None:
    """Return the publication date (YYYY-MM-DD) from the article:published_time meta tag, or None."""
    meta = soup.find("meta", attrs={"property": PUBLISHED_TIME_PROPERTY})
    if meta is None:
        return None
    published_time = (meta.get("content") or "").strip()
    if len(published_time) < ISO_DATE_LENGTH:
        return None
    return published_time[:ISO_DATE_LENGTH]


def _block_to_markdown(tag_name: str, text: str) -> str:
    """Convert one (tag_name, text) content block to a markdown paragraph."""
    if tag_name in SUBHEADING_PREFIXES:
        return f"{SUBHEADING_PREFIXES[tag_name]} {text}"
    if tag_name == LIST_ITEM_TAG:
        return f"- {text}"
    if tag_name == BLOCKQUOTE_TAG:
        return f"> {text}"
    return text


def _join_markdown_blocks(markdown_blocks: list[str]) -> str:
    """Join markdown blocks, keeping consecutive list items on adjacent lines."""
    body = ""
    for position, block in enumerate(markdown_blocks):
        if position > 0:
            previous_block = markdown_blocks[position - 1]
            both_list_items = previous_block.startswith("- ") and block.startswith("- ")
            body += "\n" if both_list_items else "\n\n"
        body += block
    return body


def article_to_markdown(html: str, article_url: str) -> str | None:
    """Convert an article page to a markdown document which contains its source URL.

    The document starts with the title, the source URL and the publication date,
    followed by the article body. The body is plain text, so the source URL is the
    main link saved for the document.

    Returns:
        The markdown document, or None when the article has no body text.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = extract_page_title(soup)
    published_date = extract_published_date(soup)
    markdown_blocks: list[str] = []
    for tag_name, text in extract_content_blocks(soup):
        if text == title and not markdown_blocks:
            continue
        markdown_block = _block_to_markdown(tag_name, text)
        if not markdown_blocks or markdown_blocks[-1] != markdown_block:
            markdown_blocks.append(markdown_block)
    if not markdown_blocks:
        return None
    header_lines = [f"# {title}", ""] if title else []
    header_lines.append(f"{SOURCE_LABEL}: {article_url}")
    if published_date is not None:
        header_lines.append(f"{PUBLISHED_LABEL}: {published_date}")
    header = "\n".join(header_lines)
    return f"{header}\n\n{_join_markdown_blocks(markdown_blocks)}\n"


def article_file_name(article_url: str) -> str:
    """Return the file name of an article document: its last URL path segment plus '.md'."""
    segments = [segment for segment in urlparse(article_url).path.split("/") if segment]
    slug = segments[-1] if segments else DEFAULT_ARTICLE_SLUG
    return f"{slug}{ARTICLE_FILE_EXTENSION}"


def normalize_article_url(url: str) -> str:
    """Normalize a URL for comparisons only.

    The scheme becomes https, the host is lowercased without 'www.', and the
    trailing slash, query and fragment are removed.
    """
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith(WWW_PREFIX):
        host = host[len(WWW_PREFIX) :]
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


async def find_indexed_article_urls(schema_name: str, project_id: int) -> set[str]:
    """Return the normalized links already saved for the documents of a project."""
    path_links = await find_path_links(schema_name, project_id)
    return {normalize_article_url(path_link.link) for path_link in path_links}


def select_missing_articles(article_urls: list[str], indexed_urls: set[str]) -> list[str]:
    """Return the article URLs, in order, whose normalized form is not among the indexed URLs."""
    return [
        article_url
        for article_url in article_urls
        if normalize_article_url(article_url) not in indexed_urls
    ]


async def write_article_documents(
    articles_folder: Path, missing_urls: list[str]
) -> list[Path]:
    """Fetch the missing articles and write them as markdown documents.

    Articles which cannot be fetched or have no body text are skipped. An existing
    document (e.g. from a run which crashed before indexing) is rewritten and
    returned, so that the article still gets indexed.

    Returns:
        The written documents, in the order of missing_urls.
    """
    articles_folder.mkdir(parents=True, exist_ok=True)
    article_files: list[Path] = []
    total_articles = len(missing_urls)
    async with create_http_client() as client:
        for position, article_url in enumerate(missing_urls, start=1):
            progress = format_progress(position, total_articles)
            try:
                html = await fetch_html(client, article_url)
            except httpx.HTTPError as e:
                logger.error(f"{progress} Failed to fetch article {article_url}: {e}")
                continue
            markdown = article_to_markdown(html, article_url)
            if markdown is None:
                logger.warning(f"{progress} No text in article {article_url}, skipped")
                continue
            file = articles_folder / article_file_name(article_url)
            file.write_text(markdown, encoding="utf-8")
            logger.info(f"{progress} Wrote article {file}")
            if file not in article_files:
                article_files.append(file)
    return article_files


async def collect_listing_article_urls(start_url: str = CLUSTRE_ARTICLES_URL) -> list[str]:
    """Crawl the article listing and return the URLs of all articles."""
    async with create_http_client() as client:
        return await collect_article_urls(client, start_url)


async def sync_clustre_articles(
    schema_name: str, project_name: str, engine: str, dry_run: bool = False
):
    """Index the Clustre articles which are not yet in the project.

    With dry_run, the missing articles are only reported, nothing is written or indexed.
    """
    await create_path_links_table(schema_name)
    project_id = await get_project_id(schema_name, project_name, engine)
    article_urls = await collect_listing_article_urls()
    if not article_urls:
        logger.warning(f"No articles found in {CLUSTRE_ARTICLES_URL}")
        return
    indexed_urls = await find_indexed_article_urls(schema_name, project_id)
    missing_urls = select_missing_articles(article_urls, indexed_urls)
    logger.info(
        f"Found {len(article_urls)} articles, {len(missing_urls)} not in {schema_name}.{project_name}"
    )
    for article_url in missing_urls:
        logger.info(f"Missing article: {article_url}")
    if dry_run or not missing_urls:
        return
    project_dir = resolve_lightrag_project_dir(schema_name, project_name, engine)
    if project_dir is None:
        return
    article_files = await write_article_documents(
        project_dir / INPUT_FOLDER / WEBSITE_ARTICLES_FOLDER, missing_urls
    )
    await index_files_into_project(project_dir, article_files)
    still_missing = select_missing_articles(
        missing_urls, await find_indexed_article_urls(schema_name, project_id)
    )
    for article_url in still_missing:
        logger.warning(f"Article still not in path links: {article_url}")


def _target_project() -> tuple[str, str, str]:
    """Return the schema, project and engine configured for the article sync."""
    return (
        os.getenv("CLUSTRE_ARTICLE_SCHEMA", "gil_fernandes"),
        os.getenv("CLUSTRE_ARTICLE_PROJECT", "clustre_full_5"),
        os.getenv("CLUSTRE_ARTICLE_ENGINE", "lightrag"),
    )


async def run_clustre_article_sync_loop():
    """Sync the Clustre articles forever, every CLUSTRE_ARTICLE_SYNC_INTERVAL_HOURS hours."""
    await run_periodic_sync(
        lambda: sync_clustre_articles(*_target_project()),
        cfg.clustre_article_sync_interval_hours,
        "Clustre article",
    )


def _parse_arguments() -> argparse.Namespace:
    """Parse the command line arguments of the article sync."""
    parser = argparse.ArgumentParser(
        description="Index the Clustre articles missing from the LightRAG project."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report the missing articles, do not write or index anything.",
    )
    return parser.parse_args()


async def main():
    arguments = _parse_arguments()
    # Imports above (lightrag) reset the logging configuration, so restore it
    init_logger()
    try:
        await sync_clustre_articles(*_target_project(), dry_run=arguments.dry_run)
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())

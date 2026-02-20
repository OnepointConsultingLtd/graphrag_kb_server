from pathlib import Path
import re

import httpx

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.service.db.common_operations import (
    extract_elements_from_path,
    get_project_id,
)
from graphrag_kb_server.service.db.db_persistence_links import (
    find_path_links,
    save_path_links,
)
from graphrag_kb_server.service.file_find_service import INPUT_FOLDER

ACCEPTED_EXTENSIONS = set([".txt", ".md"])


type DocLinks = list[tuple[str, list[str]]]


async def save_links(project_dir: Path, insert_if_not_exists: bool = False):
    simple_project = extract_elements_from_path(project_dir)
    project_id = await get_project_id(
        simple_project.schema_name,
        simple_project.project_name,
        simple_project.engine.value,
        create_if_not_exists=True,
    )
    existing_links = await find_path_links(simple_project.schema_name, project_id)
    if len(existing_links) > 0:
        logger.info(f"Links already exist for project {simple_project.project_name}")
        return
    links = extract_links(project_dir)
    verified_links = await verify_links(links)
    path_links = [
        PathLink(path=file_path, link=link, project_id=project_id)
        for file_path, links in verified_links
        for link in links
    ]
    await save_path_links(simple_project.schema_name, path_links, insert_if_not_exists)


async def verify_links(doc_links: DocLinks) -> DocLinks:
    verified_links = []
    checked_links = set()
    for doc_path, links in doc_links:
        verified_links.append((doc_path, []))
        for link in links:
            if link in checked_links:
                continue
            checked_links.add(link)
            if not await verify_link(link):
                logger.error(f"Link {link} is not valid")
            else:
                verified_links[-1][1].append(link)
                logger.info(f"Link {link} is valid")
    return verified_links


async def verify_link(link: str) -> bool:
    timeout = 5
    try:
        # Try HEAD first, following redirects
        async with httpx.AsyncClient() as client:
            response = await client.head(link, timeout=timeout, follow_redirects=True)
            if response.status_code == 200:
                return True

            # Fallback to GET for sites that don't like HEAD
            response = await client.get(link, timeout=timeout, follow_redirects=True)
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error verifying link {link}: {e}")
        return False


def extract_links(project_dir: Path) -> DocLinks:
    """Extract all URLs from .txt and .md files under project_dir/original_input.

    Returns:
        List of (file_path, list_of_urls) for each accepted file.
    """
    original_file_path = project_dir / INPUT_FOLDER
    if not original_file_path.exists():
        return []
    result: list[tuple[str, list[str]]] = []
    for original_file in original_file_path.rglob("*"):
        if original_file.is_file() and original_file.suffix in ACCEPTED_EXTENSIONS:
            text = original_file.read_text(encoding="utf-8")
            file_links = _extract_links_from_text(text)
            result.append((original_file.as_posix(), file_links))
    return result


def _extract_links_from_text(text: str) -> list[str]:
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
    # if url ends with . or ; remove it
    urls = url_pattern.findall(text)
    urls = [url.rstrip(".;)") for url in urls]
    urls = list(set(urls))  # deduplicate
    return urls


if __name__ == "__main__":
    links = _extract_links_from_text("""
Metadata
URL: https://www.onepointltd.com/onepoint-labs/
Last Scraped: 2025-08-09 14:11:04
Content Type: Web Page
""")
    print(links)
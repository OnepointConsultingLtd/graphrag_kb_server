from pathlib import Path
import re

from graphrag_kb_server.model.path_link import PathLink
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path, get_project_id
from graphrag_kb_server.service.db.db_persistence_links import save_path_links
from graphrag_kb_server.service.file_find_service import INPUT_FOLDER

ACCEPTED_EXTENSIONS = set([".txt", ".md"])


async def save_links(project_dir: Path, insert_if_not_exists: bool = False):
    simple_project = extract_elements_from_path(project_dir)
    project_id = await get_project_id(
        simple_project.schema_name,
        simple_project.project_name,
        simple_project.engine.value,
        create_if_not_exists=True,
    )
    links = extract_links(project_dir)
    path_links = [
        PathLink(path=file_path, link=link, project_id=project_id) for file_path, links in links for link in links
    ]
    await save_path_links(simple_project.schema_name, path_links, insert_if_not_exists)


def extract_links(project_dir: Path) -> list[tuple[str, list[str]]]:
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
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    # if url ends with . or ; remove it
    urls = url_pattern.findall(text)
    urls = [url.rstrip(".;)") for url in urls]
    return urls


if __name__ == "__main__":
    import asyncio
    asyncio.run(save_links(Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/lmo2"), insert_if_not_exists=True))
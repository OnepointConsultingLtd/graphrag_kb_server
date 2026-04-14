import logging
import zipfile
import re
from itertools import chain
from pathlib import Path
from urllib.parse import unquote

from graphrag_kb_server.callbacks.callback_support import BaseCallback, InfoCallback
from graphrag_kb_server.service.file_conversion import convert_pdf_or_docx_to_markdown
from graphrag_kb_server.service.file_find_service import (
    ORIGINAL_INPUT_FOLDER,
    INPUT_FOLDER,
)
from graphrag_kb_server.service.linkedin.apify_service import apify_crawl_website

log = logging.getLogger(__name__)


def create_input_folders(project_folder: Path) -> tuple[Path, Path]:
    if not project_folder.exists():
        project_folder.mkdir(parents=True, exist_ok=True)
    input_folder = project_folder / INPUT_FOLDER
    original_folder = project_folder / ORIGINAL_INPUT_FOLDER
    for target_folder in [input_folder, original_folder]:
        if not target_folder.exists():
            target_folder.mkdir(parents=True, exist_ok=True)
    return input_folder, original_folder


async def save_webpage_to_text(project_folder: Path, webpage_url: str, max_crawl_pages=100, callback: BaseCallback | None = None):
    input_folder, original_folder = create_input_folders(project_folder)
    records = await apify_crawl_website(webpage_url, max_crawl_pages=max_crawl_pages, callback=callback)
    url_text_records = [(record["url"], record["markdown"]) for record in records if record["markdown"] is not None]
    for target_folder in [input_folder, original_folder]:
        for i, (url, text) in enumerate(url_text_records):
            url_splitted = url.split("/")
            doc_name = ""
            for _ in range(len(url_splitted)):
                doc_name = url_splitted.pop().strip()
                if doc_name != "":
                    break
            # Strip query string and fragment from the last URL segment
            doc_name = re.split(r"[?#]", doc_name)[0]
            # Decode percent-encoded characters (e.g. %20 -> space)
            doc_name = unquote(doc_name)
            # Replace any remaining characters invalid in file names
            doc_name = re.sub(r'[<>:"/\\|*]', "_", doc_name).strip() or f"page_{i}"
            doc_path = target_folder / f"{doc_name}_{i}.txt"
            if len(text) > 0:
                final_text = f"""{text}

Source: {url}
"""
                try:
                    doc_path.write_text(final_text, encoding="utf-8")
                except Exception as e:
                    log.error(f"Failed to write {doc_path}: {e}")
                    log.exception(e)
            else:
                log.warning(f"No text found for {url}")


async def unzip_file(upload_folder: Path, zip_file: Path):
    input_folder, original_folder = create_input_folders(upload_folder)
    for target_folder in [input_folder, original_folder]:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            # Extract files one by one to handle individual errors
            for member in zip_ref.namelist():
                try:
                    zip_ref.extract(member, target_folder)
                except Exception as e:
                    log.error(f"Failed to extract {member} from {zip_file.name}: {e}")
    await convert_to_text(input_folder)


async def convert_to_text(input_folder: Path):
    """Convert all markdown files to text files."""
    for file in chain(input_folder.glob("**/*.pdf"), input_folder.glob("**/*.docx")):
        try:
            await convert_pdf_or_docx_to_markdown(file)
        except Exception as e:
            log.error(f"Failed to convert {file} to markdown")
            log.exception(e)
    for file in input_folder.glob("**/*.md"):
        text = file.read_text(encoding="utf-8")
        file.with_suffix(".txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    import asyncio

    class ConsoleCallback(BaseCallback):

        async def callback(self, message: str):
            print(message)

    asyncio.run(save_webpage_to_text(Path("/tmp/onepointltd"), "https://www.onepointltd.com/", 5, ConsoleCallback()))

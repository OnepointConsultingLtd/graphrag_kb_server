import logging
import zipfile

from pathlib import Path

from graphrag_kb_server.service.file_conversion import convert_pdf_to_markdown
from graphrag_kb_server.service.file_find_service import (
    ORIGINAL_INPUT_FOLDER,
    INPUT_FOLDER,
)

log = logging.getLogger(__name__)


async def unzip_file(upload_folder: Path, zip_file: Path):
    input_folder = upload_folder / INPUT_FOLDER
    original_folder = upload_folder / ORIGINAL_INPUT_FOLDER
    for target_folder in [input_folder, original_folder]:
        if not target_folder.exists():
            target_folder.mkdir(parents=True, exist_ok=True)
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
    for file in input_folder.glob("**/*.pdf"):
        try:
            await convert_pdf_to_markdown(file)
        except Exception as e:
            log.error(f"Failed to convert {file} to markdown")
            log.exception(e)
    for file in input_folder.glob("**/*.md"):
        text = file.read_text(encoding="utf-8")
        file.with_suffix(".txt").write_text(text, encoding="utf-8")

"""
Service for extracting the last updated date from a file.

For .docx files, the internal document property (core_properties.modified) is used.
For .pdf files, the /ModDate metadata entry is used.
For all other file types, the filesystem modification time is used.
"""

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.path_properties import PathProperties
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path, get_project_id
from graphrag_kb_server.service.db.db_persistence_path_properties import upsert_path_properties
from graphrag_kb_server.service.file_find_service import INPUT_FOLDER, find_original_file
from graphrag_kb_server.service.link_extraction_service import ACCEPTED_EXTENSIONS

_ACCEPTED_EXTENSIONS = set([".docx", ".pptx", ".pdf"])

# Matches the PDF date format: D:YYYYMMDDHHmmSS followed by optional timezone
# e.g. D:20240315143022+01'00' or D:20240315143022Z or D:20240315143022
_PDF_DATE_RE = re.compile(
    r"^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"
    r"(?:([Z+-])(\d{2})'(\d{2})')?",
)


def _parse_pdf_date(raw: str) -> datetime | None:
    """Parse a PDF date string into a timezone-aware datetime."""
    m = _PDF_DATE_RE.match(raw.strip())
    if not m:
        return None
    year, month, day, hour, minute, second = (int(m.group(i)) for i in range(1, 7))
    tz_sign, tz_hour, tz_min = m.group(7), m.group(8), m.group(9)
    if tz_sign in ("+", "-") and tz_hour is not None:
        offset = timedelta(hours=int(tz_hour), minutes=int(tz_min))
        tz = timezone(offset if tz_sign == "+" else -offset)
    else:
        tz = timezone.utc
    return datetime(year, month, day, hour, minute, second, tzinfo=tz)


def _last_updated_docx(path: Path) -> datetime | None:
    """Return the last modified date stored in a .docx file's core properties."""
    from docx import Document

    doc = Document(path)
    modified: datetime | None = doc.core_properties.modified
    if modified is not None and modified.tzinfo is None:
        modified = modified.replace(tzinfo=timezone.utc)
    return modified


def _last_updated_pdf(path: Path) -> datetime | None:
    """Return the last modified date stored in a PDF file's /ModDate metadata."""
    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    meta = reader.metadata
    if meta is None:
        return None
    raw = meta.get("/ModDate") or meta.get("ModDate")
    if not raw:
        return None
    # Resolve indirect object references
    if hasattr(raw, "get_object"):
        raw = raw.get_object()
    return _parse_pdf_date(str(raw))


def _last_updated_pptx(path: Path) -> datetime | None:
    """Return the last modified date stored in a .pptx file's core properties."""
    from pptx import Presentation

    prs = Presentation(path)
    modified: datetime | None = prs.core_properties.modified
    if modified is not None and modified.tzinfo is None:
        modified = modified.replace(tzinfo=timezone.utc)
    return modified


def _last_updated_filesystem(path: Path) -> datetime:
    """Return the filesystem modification time as a timezone-aware datetime."""
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc)


async def extract_last_modified_only(project_dir: Path, file_path: Path) -> datetime | None:
    original_file_path = find_original_file(
        project_dir, Path(file_path.as_posix())
    )
    if original_file_path is None:
        return None
    return get_last_updated(original_file_path)
    

async def _extract_path_properties(project_dir: Path, project_id: int) -> list[PathProperties]:
    original_file_path = project_dir / INPUT_FOLDER
    if not original_file_path.exists():
        return []
    result: list[PathProperties] = []
    for file in original_file_path.rglob("*"):
        if file.is_file() and file.suffix in ACCEPTED_EXTENSIONS:
            original_file_path = find_original_file(
                project_dir, Path(file.as_posix())
            )
            if original_file_path is None:
                continue
            last_modified = get_last_updated(original_file_path)
            if last_modified is None:
                last_modified = file.stat().st_mtime
            result.append(
                PathProperties(
                    path=file.as_posix(),
                    original_path=original_file_path.as_posix(),
                    project_id=project_id,
                    last_modified=last_modified
                )
            )
    return result


def get_last_updated(path: Path) -> datetime | None:
    """
    Return the last updated date of a file.

    Resolution order:
    - .docx  → python-docx core_properties.modified
    - .pdf   → PyPDF2 /ModDate metadata
    - other  → filesystem mtime

    Returns None only when a document-internal date cannot be read;
    filesystem fallback always succeeds for existing files.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    try:
        if suffix == ".docx":
            result = _last_updated_docx(path)
            if result is None:
                logger.warning("No modified date in docx properties, falling back to filesystem: %s", path)
                return _last_updated_filesystem(path)
            return result

        if suffix == ".pdf":
            result = _last_updated_pdf(path)
            if result is None:
                logger.warning("No /ModDate in PDF metadata, falling back to filesystem: %s", path)
                return _last_updated_filesystem(path)
            return result

        if suffix == ".pptx":
            result = _last_updated_pptx(path)
            if result is None:
                logger.warning("No modified date in pptx properties, falling back to filesystem: %s", path)
                return _last_updated_filesystem(path)
            return result

    except Exception:
        logger.exception("Failed to read document-internal date for %s, falling back to filesystem", path)
        return _last_updated_filesystem(path)

    return _last_updated_filesystem(path)


async def save_path_properties(project_dir: Path, insert_if_not_exists: bool = False):
    simple_project = extract_elements_from_path(project_dir)
    project_id = await get_project_id(
        simple_project.schema_name,
        simple_project.project_name,
        simple_project.engine.value,
        create_if_not_exists=True,
    )
    path_properties = await _extract_path_properties(project_dir, project_id)
    await upsert_path_properties(simple_project.schema_name, path_properties, insert_if_not_exists)


if __name__ == "__main__":
    last_modified = _last_updated_pdf(Path("C:/Users/gilfe/Downloads/Matter Overview .pdf"))
    print(last_modified)
    last_modified = get_last_updated(Path("C:/Users/gilfe/Downloads/Matter Overview .pdf"))
    print(last_modified)
    last_modified = _last_updated_docx(Path("C:/Users/gilfe/Downloads/January 2018 CIC - Apps v Bots - Executive Summary.docx"))
    print(last_modified)
    last_modified = _last_updated_docx(Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/original_input/clustre/Articles and PoVs/AS - Sustainability.docx"))
    print(last_modified)
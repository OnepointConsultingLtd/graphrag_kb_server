import asyncio
import logging
import re
from io import BytesIO
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


async def extract_images_from_docx(project_folder: Path, image_format: str = "png") -> list[str | None]:
    logger.info(f"Extracting images from Word documents in {project_folder}")
    docx_paths = list(project_folder.glob("**/original_input/**/*.docx"))
    tasks = [_extract_image_from_docx(docx_path, image_format) for docx_path in docx_paths]
    results = await asyncio.gather(*tasks)
    return [path for path in results if path is not None]


def _sync_extract_image_from_docx(docx_path: Path, image_format: str) -> str | None:
    from spire.doc import Document, ImageType

    image_path = get_docx_image_path(docx_path, image_format)
    error_file = docx_path.with_suffix(".error.txt")

    if image_path.exists():
        return get_docx_image_by_path(docx_path, image_format)
    if error_file.exists():
        return None

    logger.info(f"Processing {docx_path} to extract image {image_path}")
    doc = Document()
    try:
        doc.LoadFromFile(str(docx_path))
        stream = doc.SaveImageToStreams(0, ImageType.Bitmap)
        image_bytes = bytes(stream.ToArray())
        image = Image.open(BytesIO(image_bytes))
        image.save(image_path)
        logger.info(f"Extracted front page image from {docx_path} to {image_path}")
        return get_docx_image_by_path(docx_path, image_format)
    except Exception as e:
        logger.error(f"Error extracting image from {docx_path}: {e}")
        error_file.write_text(str(e), encoding="utf-8")
        return None
    finally:
        doc.Close()


async def _extract_image_from_docx(docx_path: Path, image_format: str = "png") -> str | None:
    assert docx_path.exists(), f"DOCX file {docx_path} does not exist"
    if docx_path.suffix.lower() != ".docx":
        return None
    return await asyncio.to_thread(_sync_extract_image_from_docx, docx_path, image_format)


def get_docx_image_path(docx_path: Path, image_format: str = "png") -> Path | None:
    if not docx_path.exists():
        return None
    return docx_path.with_suffix("." + image_format)


def get_docx_image_by_path(docx_path: Path, image_format: str = "png") -> str | None:
    image_path = get_docx_image_path(docx_path, image_format)
    if image_path is None or not image_path.exists():
        return None
    final_path = image_path.as_posix()
    return re.sub(r"^[^/]*/", "/", final_path)

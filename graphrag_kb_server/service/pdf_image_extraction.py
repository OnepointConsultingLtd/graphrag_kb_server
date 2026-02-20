import asyncio
import re
from pathlib import Path
from PIL import Image
import pdf2image

from graphrag_kb_server.logger import logger


async def extract_images_from_pdfs(project_folder: Path, image_format: str = "png") -> list[str | None]:
    pdf_paths = list(project_folder.glob("**/original_input/**/*.pdf"))
    tasks = [_extract_image_from_pdf(pdf_path, image_format) for pdf_path in pdf_paths]
    results = await asyncio.gather(*tasks)
    return [path for path in results if path is not None]


def _sync_extract_image(pdf_path: Path, image_format: str) -> str | None:
    image_path = get_image_path(pdf_path, image_format)
    error_file = pdf_path.with_suffix(".error.txt")
    if image_path.exists():
        return get_image_by_path(pdf_path, image_format)
    if error_file.exists():
        return None
    logger.info(f"Processing {pdf_path} to extract image {image_path}")
    try:
        images: list[Image.Image] = pdf2image.convert_from_path(
            pdf_path, first_page=1, last_page=1, fmt=image_format
        )
        if len(images) == 0:
            raise Exception(f"No images found in {pdf_path}")
        image_path_str = get_image_by_path(pdf_path, image_format)
        images[0].save(image_path_str)
        logger.info(f"Extracted front page image from {pdf_path} to {image_path_str}")
        return image_path_str
    except Exception as e:
        logger.error(f"Error extracting image from {pdf_path}: {e}")
        error_file.write_text(str(e), encoding="utf-8")
        return None


async def _extract_image_from_pdf(pdf_path: Path, image_format: str = "png") -> Path | None:
    assert pdf_path.exists(), f"PDF file {pdf_path} does not exist"
    if not pdf_path.suffix.lower() == ".pdf":
        return None
    return await asyncio.to_thread(_sync_extract_image, pdf_path, image_format)


def get_image_path(pdf_path: Path, image_format: str = "png") -> Path | None:
    if not pdf_path.exists():
        return None
    return pdf_path.with_suffix("." + image_format)


def get_image_by_path(pdf_path: Path, image_format: str = "png") -> str | None:
    image_path = get_image_path(pdf_path, image_format)
    if image_path is None or not image_path.exists():
        return None
    final_path = image_path.as_posix()
    return re.sub(r"^[^/]*/", "/", final_path)


if __name__ == "__main__":
    # Simple test
    lightrag = Path("/var/graphrag/tennants/gil_fernandes/lightrag")
    assert lightrag.exists()
    for image_path in lightrag.rglob("**/*.png"):
        image_path.unlink()
    # asyncio.run(extract_images_from_pdfs(Path("/var/graphrag/tennants/gil_fernandes/lightrag/responsible_ai_5")))
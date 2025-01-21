import sys
import asyncio
from pathlib import Path
from datetime import datetime
import re
import base64
from typing import Iterator
import zipfile

from pdf2image import convert_from_path
import pymupdf
from openai import AsyncOpenAI

from collections import defaultdict

from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg


openai_client = AsyncOpenAI()

CANNOT_CONVERT = "Cannot convert"


def __encode_image(image_path: Path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def convert_single_file(
    file: Path, use_llm: bool = False, max_retries: int = 3
) -> Path:
    assert file.exists(), f"Path {file} does not exist."
    current_datetime = datetime.now().isoformat()
    current_datetime = re.sub(r"[:.]", "", current_datetime)
    new_file_name = re.sub(r"[\s+]", "_", file.stem)
    if not use_llm:
        use_text_extraction(file, new_file_name, current_datetime)
    else:
        new_file = await convert_pdf_to_markdown(
            file, max_retries, current_datetime, new_file_name
        )
    return new_file


async def convert_pdf_to_markdown(
    file: Path, max_retries: int, current_datetime: int, new_file_name: str
):
    try:
        pages = convert_from_path(file)
        batch_size = 5
        batches = [
            pages[i : i + batch_size] for i in range(0, len(pages), batch_size)
        ]

        for i, batch in enumerate(batches):
            async_batch = [__process_page(file, max_retries, current_datetime, new_file_name, j + batch_size * i, page) for j, page in enumerate(batch)]
            results = await asyncio.gather(*async_batch)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {result}")
    except Exception as e:
        logger.exception(f"Cannot process {file}")


async def __process_page(file, max_retries, current_datetime, new_file_name, i, page):
    success = False
    retry_count = 0
    while not success and retry_count < max_retries:
        try:
            page_file = (
                    file.parent / f"{new_file_name}_{current_datetime}_{i+1}.jpg"
                )
            logger.info(f"Processing {page_file}")
            page.save(page_file, "JPEG")
            image_data = __encode_image(page_file)
            new_file = file.parent / f"{new_file_name}_{i+1}.md"
            if not new_file.exists():
                messages = __build_messages(image_data)
                response = await openai_client.chat.completions.create(
                        model=cfg.openai_api_model, messages=messages
                    )
                markdown = response.choices[0].message.content
                new_file.write_text(markdown, encoding="utf-8")
            else:
                logger.warning(f"File {new_file} already exists.")
            success = True
        except Exception:
            logger.exception("Failed to process image.")
            retry_count += 1


def __build_messages(image_data: str):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are a powerful AI system that can convert PDFs to markdown.",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Convert this pdf into markdown following these rules:
    - IGNORE HEADERS AND FOOTERS.
    - Convert any table to JSON format.
    - if you cannot convert the image to markdown, then just convert the image to plain text
    - if you cannot convert the image to plain text, write exaclty: "{CANNOT_CONVERT}" and in the line below specify the reason.
    """,
                },
                {
                    "type": "text",
                    "text": "use your built-in gpt-4 machine vision to extract and describe the text contents of my attached picture",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                    },
                },
            ],
        },
    ]

    return messages


def use_text_extraction(file: Path, new_file_name: str, current_datetime):
    new_file = file.parent / f"{new_file_name}_{current_datetime}.txt"
    doc = pymupdf.open(file)
    if new_file.exists():
        new_file.unlink()
    try:
        for page in doc:
            text_tuple = page.get_text("blocks")
            with open(new_file, "a", encoding="utf-8") as f:
                for tup in text_tuple:
                    f.write(tup[4])
    except Exception as e:
        sys.stderr.write(f"Could not write to {new_file}")
        sys.stderr.write(f"Error {e}")


def __process_folders(folders: list[str]) -> Iterator[Path]:
    for arg in folders:
        path = Path(arg)
        if path.exists():
            yield path
        else:
            sys.stderr.write(f"{path} does not exist.")


def convert_all_pdfs(folders: list[str], delete_previous: bool = False):
    for path in __process_folders(folders):
        if delete_previous:
            remove_expressions = ["**/*.txt", "**/*.jpg", "**/*.md"]
            for expression in remove_expressions:
                for txt_file in path.rglob(expression):
                    txt_file.unlink()
        pdfs = path.rglob("**/*.pdf")
        for pdf in pdfs:
            print(f"Started processing {pdf}")
            asyncio.run(convert_single_file(pdf, use_llm=True))
            print(f"Processed {pdf}")


def compact_files(folders: list[str]) -> dict[Path, list[Path]]:
    all_aggregate_files = {}
    for path in __process_folders(folders):
        md_files = path.rglob("**/*.md")
        aggregate_dict = defaultdict(list)
        for md_file in md_files:
            if not "_aggregate" in md_file.name:
                key = re.sub(r"(.+)\_\d+\.md", r"\1", md_file.name)
                aggregate_dict[md_file.parent/f"{key}_aggregate.md"].append(md_file)
        aggregate_files = []
        for target_file, pages in aggregate_dict.items():
            with open(target_file, "wt", encoding="utf-8") as f:
                for page in pages:
                    content = page.read_text(encoding="utf-8")
                    if not CANNOT_CONVERT in content:
                        f.write(content)
                f.write("\n")
            aggregate_files.append(target_file)
        all_aggregate_files[path] = aggregate_files
    return all_aggregate_files


def zip_md_files(folder_files: dict[Path, list[Path]]) -> list[Path]:
    zipped_files = []
    for folder, files in folder_files.items():
        output_zip = folder.parent/f"{folder.name}.zip"
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                zipf.write(file, arcname=file.relative_to(folder.parent))
        zipped_files.append(output_zip)
    return zipped_files

if __name__ == "__main__":

    if len(sys.argv) < 3:
        sys.stderr.write("""Please specify the command and the directory
Example: convert python ./graphrag_kb_server/service/pdf_to_text.py /development/onepoint/thinqwin/graphrag_kb_server/docs/hypergility
""")
        sys.exit(1)

    command = sys.argv[1]
    directories = sys.argv[2:]

    match command:
        case "convert":
            convert_all_pdfs(directories, False)
        case "compact":
            folder_files = compact_files(directories)
            zip_files = zip_md_files(folder_files)
            for zip_file in zip_files:
                print(zip_file)
        case _:
            sys.stderr.write(f"Command {command} not found.")

from pathlib import Path
import re
import zipfile
from typing import AsyncIterator
from lightrag import LightRAG
from lightrag.base import DocProcessingStatus

from graphrag_kb_server.model.project import GenerationStatus
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER


def override_lightrag_prompt():
    from lightrag import prompt as lightrag_prompt

    extra = """
    9.  **Canonicalization Rules:**
        *   Always use the full, unabbreviated form of an entity name (e.g. "Artificial Intelligence", not "AI"; "United Kingdom", not "UK").
        *   For people, always use the full formal name (e.g. "Robert Baldock", not "Rob" or "Robert").
        *   If you are unsure of the full name, use the most complete form present in the text.
    """
    lightrag_prompt.PROMPTS["entity_extraction_system_prompt"] += extra


override_lightrag_prompt()


TIKTOKEN_SPECIAL_TOKENS = re.compile(
    r"<\|endoftext\|>|<\|fim_prefix\|>|<\|fim_middle\|>|<\|fim_suffix\|>"
    r"|<\|endofprompt\|>|<\|im_start\|>|<\|im_end\|>|<\|im_sep\|>"
)


def _sanitize_for_tiktoken(text: str) -> str:
    """Remove tiktoken special tokens from text to prevent encoding errors."""
    return TIKTOKEN_SPECIAL_TOKENS.sub("", text)


DOC_STATUS_PAGE_SIZE = 200


def zip_entry_to_indexed_relative_path(zip_entry: str) -> str:
    """Maps a zip entry to the relative path of the text file that is indexed for it.

    Uploaded pdf, docx, pptx, md and audio files are converted to a text file with
    the same stem, so every entry is mapped to its ``.txt`` counterpart.
    """
    return Path(zip_entry).with_suffix(".txt").as_posix()


def find_files_to_index(
    input_folder: Path, all_files: list[Path], zip_entries: list[str]
) -> list[Path]:
    """Selects the text files in the input folder which correspond to the zip entries.

    Files are matched on their exact path relative to the input folder, so files
    with similar names or with the same name in other folders are not selected.
    """
    uploaded_paths = {
        zip_entry_to_indexed_relative_path(entry)
        for entry in zip_entries
        if not entry.endswith("/")
    }
    return [
        file
        for file in all_files
        if file.relative_to(input_folder).as_posix() in uploaded_paths
    ]


async def iterate_indexed_documents(
    rag: LightRAG,
) -> AsyncIterator[tuple[str, DocProcessingStatus]]:
    """Iterates over all the (doc_id, document status) pairs in the LightRAG index."""
    page = 1
    while True:
        docs, total = await rag.doc_status.get_docs_paginated(
            page=page, page_size=DOC_STATUS_PAGE_SIZE, sort_field="id"
        )
        for doc in docs:
            yield doc
        if page * DOC_STATUS_PAGE_SIZE >= total or not docs:
            return
        page += 1


def indexed_relative_path(stored_path: str, input_folder: Path) -> str | None:
    """Converts the file path stored in the index to a path relative to the input folder.

    The stored path can start with a different prefix than the current input folder,
    e.g. if the project was indexed in another location or in a container. In that
    case the path after the first ``/input/`` folder is used.

    Returns:
        The relative path or None if the stored path is not inside an input folder.
    """
    normalized_path = stored_path.replace("\\", "/")
    input_prefix = input_folder.resolve().as_posix().rstrip("/") + "/"
    if normalized_path.startswith(input_prefix):
        return normalized_path[len(input_prefix) :]
    marker = f"/{INPUT_FOLDER}/"
    marker_index = normalized_path.find(marker)
    if marker_index == -1:
        return None
    return normalized_path[marker_index + len(marker) :]


async def find_doc_ids_by_relative_path(
    rag: LightRAG, input_folder: Path, relative_path: str
) -> list[str]:
    """Finds the ids of all the indexed documents which were inserted from a file.

    The file is identified by its path relative to the input folder, which makes
    the lookup independent of where the project was located when it was indexed.
    More than one id can be returned if several versions of the same file were
    indexed before.
    """
    return [
        doc_id
        async for doc_id, doc in iterate_indexed_documents(rag)
        if indexed_relative_path(doc.file_path, input_folder) == relative_path
    ]


async def list_indexed_file_paths(rag: LightRAG, input_folder: Path) -> list[str]:
    """Lists the indexed files which can be removed from the index.

    Returns:
        The sorted, unique paths of the indexed files relative to the input folder.
        Documents which were not inserted from an input folder are left out, as
        they cannot be addressed for removal.
    """
    relative_paths = set()
    async for _, doc in iterate_indexed_documents(rag):
        relative_path = indexed_relative_path(doc.file_path, input_folder)
        if relative_path:
            relative_paths.add(relative_path)
    return sorted(relative_paths)


async def adelete_file_from_index(
    rag: LightRAG, input_folder: Path, relative_path: str
) -> int:
    """Removes every indexed version of a file from the LightRAG index.

    Deletes the document chunks and the entities and relations only supported by
    them. Does nothing if the file was never indexed.

    Returns:
        The number of indexed documents which were deleted.

    Raises:
        RuntimeError: If LightRAG failed to delete one of the documents.
    """
    deleted = 0
    for doc_id in await find_doc_ids_by_relative_path(
        rag, input_folder, relative_path
    ):
        result = await rag.adelete_by_doc_id(doc_id)
        if result.status == "success":
            deleted += 1
        elif result.status != "not_found":
            raise RuntimeError(
                f"Failed to delete {relative_path} ({doc_id}) from the index: {result.message}"
            )
    return deleted


async def acreate_lightrag(
    create_if_not_exists: bool = True,
    project_folder: Path | None = None,
    incremental: bool = False,
    zip_file: Path | None = None,
) -> GenerationStatus:
    if not create_if_not_exists:
        if project_folder.exists():
            return GenerationStatus.EXISTS
    rag = await initialize_rag(project_folder)
    working_dir = Path(rag.working_dir)
    input_folder = working_dir.parent / INPUT_FOLDER
    assert input_folder.exists(), f"Input folder does not exist: {input_folder}"
    all_files = list(input_folder.rglob("**/*.txt"))
    if incremental:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_entries = zip_ref.namelist()
        files_to_index = find_files_to_index(input_folder, all_files, zip_entries)
        # Replace the previously indexed versions of the updated files
        for file in files_to_index:
            await adelete_file_from_index(
                rag, input_folder, file.relative_to(input_folder).as_posix()
            )
        await lightrag_index(rag, files_to_index)
    else:
        await lightrag_index(rag, all_files)
    return GenerationStatus.CREATED


async def lightrag_index(rag: LightRAG, files_to_index: list[Path]):
    count = len(files_to_index)
    assert count > 0, "No files to index"
    tolerance = 3
    for i, file in enumerate(files_to_index):
        try:
            content = _sanitize_for_tiktoken(file.read_text(encoding="utf-8"))
            filename_header = f"Document: {file.stem.replace('_', ' ')}\n\n"
            await rag.ainsert(filename_header + content, file_paths=file.as_posix())
            logger.info("########################################################")
            logger.info(f"Indexed {i+1}/{count} files: {file}")
            logger.info("########################################################")
        except Exception as e:
            logger.error(f"Error indexing file {file}: {e}")
            logger.exception(e)
            if tolerance > 0:
                tolerance -= 1
                logger.info(f"Tolerance reduced to {tolerance} times")
            else:
                raise e

    logger.info(f"Indexed {count} files")

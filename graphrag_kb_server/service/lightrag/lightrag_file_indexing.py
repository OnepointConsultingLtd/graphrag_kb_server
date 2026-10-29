import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

from lightrag import LightRAG

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.file_conversion import (
    convert_pdf_docx_pptx_to_markdown,
)
from graphrag_kb_server.service.index_support import create_input_folders
from graphrag_kb_server.service.indexing_job_registry import (
    IndexingJobRegistry,
    indexing_job_registry,
)
from graphrag_kb_server.service.lightrag.lightrag_file_removal import (
    delete_files_from_disk,
)
from graphrag_kb_server.service.lightrag.lightrag_index_support import (
    adelete_file_from_index,
    lightrag_index,
)
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.utils.file_support import write_uploaded_file

TEXT_EXTENSION: Final = ".txt"
MARKDOWN_EXTENSION: Final = ".md"
PDF_EXTENSION: Final = ".pdf"
ALLOWED_INDEX_FILE_EXTENSIONS: Final = frozenset(
    {TEXT_EXTENSION, MARKDOWN_EXTENSION, PDF_EXTENSION}
)
MAX_INDEX_FILES: Final = 5

StatusCallback = Callable[[IndexingStatus, str], None]


@dataclass(frozen=True)
class UploadedFile:
    """A file received in a multipart request."""

    file_name: str
    base64_content: bytes


@dataclass(frozen=True)
class PreparedFile:
    """An uploaded file stored in the work folder together with its text version."""

    uploaded_file_name: str
    original_file: Path
    text_file: Path


def no_status_update(_status: IndexingStatus, _message: str):
    """Status callback which ignores the status updates, e.g. for synchronous requests."""


def indexed_message(file_count: int, project: str) -> str:
    """Describes a successful indexing of the uploaded files."""
    return f"{file_count} file(s) indexed successfully in index {project}"


def submitted_message(file_count: int, project: str) -> str:
    """Describes uploaded files which are waiting to be indexed in the background."""
    return f"{file_count} file(s) submitted for indexing in index {project}"


def normalize_file_stem(file_name: str) -> str:
    """Converts an uploaded file name to the stem used for the files in the project.

    Directories are removed and whitespace is replaced with underscores, which is
    the same naming used by the PDF to markdown conversion. Using one naming for
    all file types keeps the indexed file name predictable.
    """
    return re.sub(r"\s+", "_", Path(file_name).stem.strip())


def indexed_file_name(file_name: str) -> str:
    """Returns the name of the text file which is indexed for an uploaded file."""
    return f"{normalize_file_stem(file_name)}{TEXT_EXTENSION}"


def previous_version_names(file_name: str) -> list[str]:
    """Returns the names under which an earlier version of the file can be indexed.

    Files uploaded in a zip keep the whitespace in their names, whereas this
    endpoint replaces it, so both names are searched in the index.
    """
    names = [f"{Path(file_name).stem}{TEXT_EXTENSION}", indexed_file_name(file_name)]
    return list(dict.fromkeys(names))


def validate_uploaded_files(file_names: list[str]) -> str | None:
    """Checks the number, the types and the names of the uploaded files.

    Returns:
        A description of the problem or None if the files are valid.
    """
    if not file_names:
        return "Please upload at least one file."
    if len(file_names) > MAX_INDEX_FILES:
        return f"Please upload at most {MAX_INDEX_FILES} files. Received {len(file_names)} files."
    invalid_files = [
        file_name
        for file_name in file_names
        if Path(file_name).suffix.lower() not in ALLOWED_INDEX_FILE_EXTENSIONS
    ]
    if invalid_files:
        allowed = ", ".join(sorted(ALLOWED_INDEX_FILE_EXTENSIONS))
        return f"Unsupported file type: {', '.join(invalid_files)}. Allowed types: {allowed}."
    stems = [normalize_file_stem(file_name) for file_name in file_names]
    if any(stem.strip(".") == "" for stem in stems):
        return "Invalid file name. Every file needs a name before its extension."
    duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
    if duplicates:
        return f"Duplicate file names: {', '.join(duplicates)}."
    return None


async def convert_to_text(original_file: Path) -> Path:
    """Creates the text version of a text, markdown or PDF file in the same folder.

    PDF files are converted to markdown with an LLM first.

    Returns:
        The text file.
    """
    suffix = original_file.suffix.lower()
    if suffix == TEXT_EXTENSION:
        return original_file
    if suffix == MARKDOWN_EXTENSION:
        markdown_file = original_file
    elif suffix == PDF_EXTENSION:
        markdown_file = await convert_pdf_docx_pptx_to_markdown(original_file)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    text_file = original_file.with_suffix(TEXT_EXTENSION)
    shutil.copyfile(markdown_file, text_file)
    return text_file


async def prepare_uploaded_file(
    uploaded_file: UploadedFile, work_folder: Path
) -> PreparedFile:
    """Writes an uploaded file into the work folder and creates its text version.

    Every file is written with its normalised name into a folder that is not
    shared with other files, so that the PDF conversion never appends to or reuses
    the output of an earlier conversion.
    """
    suffix = Path(uploaded_file.file_name).suffix.lower()
    original_file = (
        work_folder / f"{normalize_file_stem(uploaded_file.file_name)}{suffix}"
    )
    write_uploaded_file(uploaded_file.base64_content, original_file)
    text_file = await convert_to_text(original_file)
    return PreparedFile(
        uploaded_file_name=uploaded_file.file_name,
        original_file=original_file,
        text_file=text_file,
    )


async def remove_previous_versions(
    rag: LightRAG, project_folder: Path, file_name: str
) -> int:
    """Removes the earlier versions of an uploaded file from the index and from disk.

    Returns:
        The number of documents which were deleted from the index.
    """
    input_folder, _ = create_input_folders(project_folder)
    deleted_documents = 0
    for previous_name in previous_version_names(file_name):
        deleted_documents += await adelete_file_from_index(
            rag, input_folder, previous_name
        )
        delete_files_from_disk(project_folder, previous_name)
    return deleted_documents


def install_prepared_file(prepared_file: PreparedFile, project_folder: Path) -> Path:
    """Copies the original file and its text version into the project folders.

    Returns:
        The text file in the input folder which needs to be indexed.
    """
    input_folder, original_folder = create_input_folders(project_folder)
    shutil.copyfile(
        prepared_file.original_file, original_folder / prepared_file.original_file.name
    )
    indexed_text_file = input_folder / indexed_file_name(
        prepared_file.uploaded_file_name
    )
    shutil.copyfile(prepared_file.text_file, indexed_text_file)
    return indexed_text_file


async def replace_files_in_index(
    project_folder: Path,
    uploaded_files: list[UploadedFile],
    on_status: StatusCallback = no_status_update,
    registry: IndexingJobRegistry = indexing_job_registry,
) -> int:
    """Indexes the uploaded files, replacing any earlier version in the index.

    All files are converted to text before the index is modified, so a failed
    conversion leaves the project unchanged. Jobs for the same project run one
    after the other.

    Args:
        project_folder: The folder of an existing LightRAG project.
        uploaded_files: The text, markdown or PDF files to index.
        on_status: Called whenever the indexing reaches a new stage.
        registry: Provides the lock which serialises the jobs of the project.

    Returns:
        The number of indexed files.
    """
    from graphrag_kb_server.service.project import (
        prepare_project_extras,
        write_project_file,
    )

    file_count = len(uploaded_files)
    work_folder = cfg.upload_dir / f"index_files_{uuid.uuid4().hex}"
    async with registry.project_lock(project_folder):
        modifying_index = False
        try:
            on_status(
                IndexingStatus.PREPARING, f"Converting {file_count} file(s) to text"
            )
            work_folder.mkdir(parents=True, exist_ok=True)
            prepared_files = [
                await prepare_uploaded_file(uploaded_file, work_folder)
                for uploaded_file in uploaded_files
            ]

            on_status(IndexingStatus.IN_PROGRESS, f"Indexing {file_count} file(s)")
            modifying_index = True
            write_project_file(project_folder, IndexingStatus.IN_PROGRESS)
            rag = await initialize_rag(project_folder)
            files_to_index = []
            for prepared_file in prepared_files:
                await remove_previous_versions(
                    rag, project_folder, prepared_file.uploaded_file_name
                )
                files_to_index.append(
                    install_prepared_file(prepared_file, project_folder)
                )
            await lightrag_index(rag, files_to_index, tolerance=0)
            await prepare_project_extras(project_folder)
            write_project_file(project_folder, IndexingStatus.COMPLETED)
            return len(files_to_index)
        except Exception:
            if modifying_index:
                write_project_file(project_folder, IndexingStatus.FAILED)
            logger.exception(f"Failed to index files in {project_folder}")
            raise
        finally:
            shutil.rmtree(work_folder, ignore_errors=True)


async def run_indexing_job(
    job_id: str,
    project_folder: Path,
    uploaded_files: list[UploadedFile],
    registry: IndexingJobRegistry = indexing_job_registry,
):
    """Indexes the uploaded files in the background and records the progress in the job.

    Errors are stored in the job instead of being raised, as nobody awaits the job.
    """

    def update_job_status(status: IndexingStatus, message: str):
        registry.update_status(job_id, status, message)

    try:
        indexed_count = await replace_files_in_index(
            project_folder, uploaded_files, update_job_status, registry
        )
        registry.update_status(
            job_id,
            IndexingStatus.COMPLETED,
            indexed_message(indexed_count, project_folder.name),
        )
    except Exception as e:
        registry.update_status(
            job_id,
            IndexingStatus.FAILED,
            f"Failed to index files in index {project_folder.name}",
            error=str(e),
        )

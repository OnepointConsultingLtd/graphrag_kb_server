from pathlib import Path

from lightrag import LightRAG

from graphrag_kb_server.service.file_find_service import ORIGINAL_INPUT_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_index_support import (
    adelete_file_from_index,
    list_indexed_file_paths,
    zip_entry_to_indexed_relative_path,
)
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag


def resolve_inside_folder(folder: Path, relative_path: str) -> Path:
    """Resolves a relative path inside a folder.

    Raises:
        ValueError: If the path is absolute or escapes the folder, e.g. via "..".
    """
    resolved_folder = folder.resolve()
    resolved_path = (resolved_folder / relative_path).resolve()
    if resolved_path == resolved_folder or not resolved_path.is_relative_to(
        resolved_folder
    ):
        raise ValueError(f"Invalid file path: {relative_path}")
    return resolved_path


def delete_files_from_disk(project_folder: Path, relative_path: str) -> list[Path]:
    """Deletes the indexed text file and the original uploaded file(s) from disk.

    The original files share the relative path and stem of the file, but can have
    any extension, e.g. ``report.pdf`` for the indexed ``report.txt``.

    Returns:
        The files which were deleted.
    """
    text_relative_path = zip_entry_to_indexed_relative_path(relative_path)
    input_file = resolve_inside_folder(project_folder / INPUT_FOLDER, text_relative_path)
    original_file = resolve_inside_folder(
        project_folder / ORIGINAL_INPUT_FOLDER, text_relative_path
    )
    candidates = [input_file]
    if original_file.parent.exists():
        candidates.extend(original_file.parent.glob(f"{original_file.stem}.*"))
    deleted = []
    for candidate in candidates:
        if candidate.is_file():
            candidate.unlink()
            deleted.append(candidate)
    return deleted


async def remove_file_from_project(
    project_folder: Path,
    relative_path: str,
    rag: LightRAG | None = None,
    delete_unindexed: bool = False,
) -> tuple[int, list[Path]]:
    """Removes a file from the LightRAG index and from the project folders.

    The files on disk are only deleted if the file was found in the index, so
    that a failed lookup does not leave documents in the index without a file.

    Args:
        project_folder: The folder of the LightRAG project.
        relative_path: The path of the file relative to the project input folder.
        rag: The LightRAG instance. Initialised from the project folder if missing.
        delete_unindexed: Delete the files from disk even if the file is not indexed.

    Returns:
        The number of indexed documents deleted and the files deleted from disk.

    Raises:
        ValueError: If the path is outside the project input folder.
    """
    input_folder = project_folder / INPUT_FOLDER
    text_relative_path = zip_entry_to_indexed_relative_path(relative_path)
    resolve_inside_folder(input_folder, text_relative_path)
    rag = rag or await initialize_rag(project_folder)
    deleted_documents = await adelete_file_from_index(
        rag, input_folder, text_relative_path
    )
    if deleted_documents == 0 and not delete_unindexed:
        return 0, []
    return deleted_documents, delete_files_from_disk(project_folder, relative_path)


async def list_removable_files(
    project_folder: Path, rag: LightRAG | None = None
) -> list[str]:
    """Lists the files of a project which can be removed with `remove_file_from_project`.

    Returns:
        The sorted paths of the indexed files relative to the project input folder.
    """
    rag = rag or await initialize_rag(project_folder)
    return await list_indexed_file_paths(rag, project_folder / INPUT_FOLDER)

from pathlib import Path
import zipfile
from lightrag import LightRAG

from graphrag_kb_server.model.project import GenerationStatus
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.lightrag.lightrag_constants import INPUT_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_centrality import lightrag_cache


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
    input_folder = rag.working_dir.parent / INPUT_FOLDER
    assert input_folder.exists(), f"Input folder does not exist: {input_folder}"
    all_files = list(input_folder.rglob("**/*.txt"))
    if incremental:
        # open the zip file and list the files
        files_to_index = []
        zip_files = []
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith(".txt"):
                    zip_files.append(file)
        for file in all_files:
            for f in zip_files:
                if f.split("/")[-1] in file.name:
                    files_to_index.append(file)
                    break
        lightrag_cache.clear(project_folder)
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
            await rag.ainsert(file.read_text(encoding="utf-8"), file_paths=file.as_posix())
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

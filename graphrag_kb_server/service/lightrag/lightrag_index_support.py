from pathlib import Path
from lightrag import LightRAG

from graphrag_kb_server.model.project import GenerationStatus
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag

INPUT_FOLDER = "input"


async def acreate_lightrag(
    create_if_not_exists: bool = True, project_folder: Path | None = None
) -> GenerationStatus:
    if not create_if_not_exists:
        if project_folder.exists():
            return GenerationStatus.EXISTS
    rag = await initialize_rag(project_folder)
    await lightrag_index(rag)
    return GenerationStatus.CREATED


async def lightrag_index(rag: LightRAG):
    input_folder = rag.working_dir.parent / INPUT_FOLDER
    assert input_folder.exists(), f"Input folder does not exist: {input_folder}"
    all_files = list(input_folder.rglob("**/*.txt"))
    count = len(all_files)
    assert count > 0, "No files to index"
    for i, file in enumerate(all_files):
        await rag.ainsert(file.read_text(encoding="utf-8"))
        logger.info("########################################################")
        logger.info(f"Indexed {i+1}/{count} files: {file}")
        logger.info("########################################################")

    logger.info(f"Indexed {count} files")

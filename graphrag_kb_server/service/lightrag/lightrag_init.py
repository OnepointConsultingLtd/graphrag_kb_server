from pathlib import Path

from lightrag import LightRAG
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

from graphrag_kb_server.config import lightrag_cfg


async def initialize_rag(project_folder: Path) -> LightRAG:
    working_dir = project_folder / LIGHTRAG_FOLDER
    if not working_dir.exists():
        working_dir.mkdir(parents=True, exist_ok=True)
    llm_model_func = gpt_4o_mini_complete
    match lightrag_cfg.lightrag_model:
        case "gpt-4o-mini":
            llm_model_func = gpt_4o_mini_complete
        case "gpt-4o":
            llm_model_func = gpt_4o_complete
        case _:
            raise ValueError(f"Invalid LightRAG model: {lightrag_cfg.lightrag_model}")
    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=openai_embed,
        llm_model_func=llm_model_func,
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag
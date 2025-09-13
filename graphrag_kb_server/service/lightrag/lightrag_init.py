from pathlib import Path

from lightrag import LightRAG
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from lightrag.llm.openai import openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

from graphrag_kb_server.service.lightrag.lightrag_model_support import select_model_func
from graphrag_kb_server.config import lightrag_cfg
from graphrag_kb_server.utils.cache import GenericProjectSimpleCache


lightrag_cache = GenericProjectSimpleCache[LightRAG]()


async def initialize_rag(project_folder: Path) -> LightRAG:
    lightrag = lightrag_cache.get(project_folder)
    if lightrag:
        return lightrag
    working_dir = project_folder / LIGHTRAG_FOLDER
    if not working_dir.exists():
        working_dir.mkdir(parents=True, exist_ok=True)
    llm_model_func = select_model_func()
    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=openai_embed,
        llm_model_func=llm_model_func,
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()
    lightrag_cache.set(project_folder, rag)
    # Enable LLM cache for now
    rag.llm_response_cache.global_config["enable_llm_cache"] = True
    return rag

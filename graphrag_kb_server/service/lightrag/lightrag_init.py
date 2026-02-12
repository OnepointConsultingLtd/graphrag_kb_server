from pathlib import Path
import os
import json
import asyncio

from lightrag import LightRAG
from lightrag.base import BaseGraphStorage, BaseKVStorage, BaseVectorStorage, DocStatusStorage
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from lightrag.llm.openai import openai_embed
from lightrag.kg.shared_storage import get_namespace_data, initialize_pipeline_status

from graphrag_kb_server.service.lightrag.lightrag_model_support import select_model_func
from graphrag_kb_server.utils.cache import GenericProjectSimpleCache


lightrag_cache = GenericProjectSimpleCache[LightRAG]()


async def initialize_rag(project_folder: Path) -> LightRAG:
    lightrag = lightrag_cache.get(project_folder)
    if lightrag:
        return lightrag
    working_dir = project_folder / LIGHTRAG_FOLDER
    if not await asyncio.to_thread(working_dir.exists):
        await asyncio.to_thread(working_dir.mkdir, parents=True, exist_ok=True)
    llm_model_func = select_model_func()
    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=openai_embed,
        llm_model_func=llm_model_func,
    )
    await rag.initialize_storages()
    await initialize_storages(rag)
    await initialize_pipeline_status()
    lightrag_cache.set(project_folder, rag)
    # Enable LLM cache for now
    rag.llm_response_cache.global_config["enable_llm_cache"] = False
    return rag


async def initialize_storages(rag: LightRAG):
    """
    Makes sure that the storages are initialized and the data is loaded from the file.
    This fixes problems with non loaded JSON storage data.
    """
    coroutines = []
    for storage in (
        rag.full_docs,
        rag.text_chunks,
        rag.full_entities,
        rag.full_relations,
        rag.entity_chunks,
        rag.relation_chunks,
        rag.entities_vdb,
        rag.relationships_vdb,
        rag.chunks_vdb,
        rag.chunk_entity_relation_graph,
        rag.llm_response_cache,
        rag.doc_status,
    ):
        coroutines.append(_process_single_storage(storage))
    await asyncio.gather(*coroutines)


async def _process_single_storage(storage: BaseKVStorage | DocStatusStorage | BaseVectorStorage | BaseGraphStorage | None) -> None:
    if not storage:
        return

    file_name = getattr(storage, "_file_name", None)
    if file_name:
        loaded_data = await load_json(file_name) or {}
        storage._data = await get_namespace_data(storage.final_namespace)
        storage._data.update(loaded_data)
    else:
        await storage.initialize()


async def load_json(file_name):
    def _load_json_sync():
        if not os.path.exists(file_name):
            return None
        with open(file_name, encoding="utf-8-sig") as f:
            return json.load(f)
    
    return await asyncio.to_thread(_load_json_sync)
from pathlib import Path
import asyncio
from typing import Any

from lightrag import LightRAG
from lightrag.base import (
    BaseGraphStorage,
    BaseKVStorage,
    BaseVectorStorage,
    DocStatusStorage,
)
from lightrag.llm.openai import openai_embed
from lightrag.kg.shared_storage import get_namespace_data, initialize_pipeline_status

from graphrag_kb_server.service.lightrag.lightrag_model_support import select_model_func
from graphrag_kb_server.utils.cache import GenericProjectSimpleCache
from graphrag_kb_server.utils.quick_json_loader import load_json
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER


lightrag_cache = GenericProjectSimpleCache[LightRAG]()


from lightrag.operate import chunking_by_token_size
from lightrag.utils import Tokenizer


def chunking_with_special_tokens(
    tokenizer: Tokenizer,
    content: str,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    overlap_token_size: int = 128,
    max_token_size: int = 1024,
) -> list[dict[str, Any]]:
    """
    Custom chunking function that handles special tokens properly.
    Uses the raw tiktoken encoder with allowed_special="all" when available,
    so content with special tokens does not raise ValueError.
    """

    # LightRAG's Tokenizer.encode() does not accept allowed_special; the underlying
    # tiktoken does. TiktokenTokenizer stores the raw encoder in .tokenizer.
    class SafeTokenizer:
        def __init__(self, base_tokenizer):
            self.base_tokenizer = base_tokenizer
            self._raw = getattr(base_tokenizer, "tokenizer", None)

        def encode(self, text: str, **kwargs):
            if self._raw is not None:
                return self._raw.encode(
                    text, allowed_special="all", disallowed_special=(), **kwargs
                )
            return self.base_tokenizer.encode(text)

        def decode(self, tokens: list[int]) -> str:
            """Decode tokens back to text using the base tokenizer."""
            return self.base_tokenizer.decode(tokens)

    safe_tokenizer = SafeTokenizer(tokenizer)
    return chunking_by_token_size(
        safe_tokenizer,
        content,
        split_by_character,
        split_by_character_only,
        overlap_token_size,
        max_token_size,
    )


async def initialize_rag(project_folder: Path) -> LightRAG:
    lightrag = lightrag_cache.get(project_folder)
    if lightrag:
        return lightrag
    working_dir = (project_folder / LIGHTRAG_FOLDER).resolve()
    await asyncio.to_thread(working_dir.mkdir, parents=True, exist_ok=True)
    # Pass absolute path as string so LightRAG and JSON storage resolve paths correctly (e.g. on Windows)
    working_dir_str = str(working_dir)
    llm_model_func = select_model_func()
    rag = LightRAG(
        working_dir=working_dir_str,
        workspace=working_dir_str,
        embedding_func=openai_embed,
        llm_model_func=llm_model_func,
        chunking_func=chunking_with_special_tokens,
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
        coroutines.append(_process_single_storage(storage, rag.workspace))
    await asyncio.gather(*coroutines)


async def _process_single_storage(
    storage: (
        BaseKVStorage | DocStatusStorage | BaseVectorStorage | BaseGraphStorage | None
    ),
    workspace: str,
) -> None:
    if not storage:
        return

    file_name = getattr(storage, "_file_name", None)
    if file_name:
        loaded_data = await load_json(file_name) or {}
        storage._data = await get_namespace_data(storage.namespace, workspace=workspace)
        storage._data.update(loaded_data)
    else:
        await storage.initialize()

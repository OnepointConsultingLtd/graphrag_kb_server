from pathlib import Path
from typing import Literal
from dataclasses import asdict

from lightrag import LightRAG, QueryParam
from lightrag.operate import kg_query
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag


async def lightrag_search(
    project_folder: Path,
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"],
    only_need_context: bool = False,
) -> str:
    rag: LightRAG = await initialize_rag(project_folder)
    param = QueryParam(mode=mode, only_need_context=only_need_context)
    if mode in ["local", "global", "hybrid", "mix"]:
        global_config = asdict(rag)
        return await kg_query(
            query.strip(),
            rag.chunk_entity_relation_graph,
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.text_chunks,
            param,
            global_config,
            hashing_kv=rag.llm_response_cache,
            system_prompt=None,
            chunks_vdb=rag.chunks_vdb,
        )
    return await rag.aquery(
        query, param
    )

from pathlib import Path
from typing import Literal

from lightrag import LightRAG, QueryParam
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag


async def lightrag_search(
    project_folder: Path,
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"],
    only_need_context: bool = False,
) -> str:
    rag: LightRAG = await initialize_rag(
        project_folder
    )
    return await rag.aquery(query, QueryParam(mode=mode, only_need_context=only_need_context))

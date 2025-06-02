from dataclasses import asdict

from lightrag import LightRAG, QueryParam
from lightrag.operate import kg_query
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.model.rag_parameters import QueryParameters
from lightrag.operate import PROMPTS

async def lightrag_search(
    query_params: QueryParameters,
    only_need_context: bool = False,
) -> str:
    project_folder = query_params.context_params.project_dir
    query = query_params.context_params.query
    system_prompt_additional = query_params.system_prompt_additional or ""
    mode = query_params.search
    rag: LightRAG = await initialize_rag(project_folder)
    param = QueryParam(mode=mode, only_need_context=only_need_context)
    system_prompt = f"""{system_prompt_additional}

In case of a coloquial question or non context related sentence you can respond to it without focusing on the context.
{PROMPTS["rag_response"]}
"""
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
            system_prompt=system_prompt,
            chunks_vdb=rag.chunks_vdb,
        )
    return await rag.aquery(query, param)

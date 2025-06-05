from dataclasses import asdict
from typing import AsyncIterator
from functools import partial
import json
import os

import numpy as np

from lightrag import LightRAG, QueryParam

from lightrag.operate import (
    PROMPTS,
    extract_keywords_only,
    get_keywords_from_query,
    handle_cache,
    save_to_cache,
    CacheData,
    compute_args_hash,
    get_conversation_turns,
    process_combine_contexts,
    _get_node_data,
    _get_edge_data,
    _get_vector_context,
)
from lightrag.base import BaseGraphStorage, BaseVectorStorage, BaseKVStorage

from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.chat_response import ChatResponse


def _combine_keywords(old_keywords: list[str], new_keywords: list[str]) -> list[str]:
    return list(set(old_keywords + new_keywords))


async def lightrag_search(
    query_params: QueryParameters,
    only_need_context: bool = False,
) -> str:
    project_folder = query_params.context_params.project_dir
    query = query_params.context_params.query
    system_prompt_additional = query_params.system_prompt_additional or ""
    mode = query_params.search
    rag: LightRAG = await initialize_rag(project_folder)
    param = QueryParam(
        mode=mode,
        only_need_context=only_need_context,
        hl_keywords=query_params.hl_keywords,
        ll_keywords=query_params.ll_keywords,
    )
    if query_params.system_prompt:
        system_prompt = query_params.system_prompt
    else:
        system_prompt = f"""{system_prompt_additional}

In case of a coloquial question or non context related sentence you can respond to it without focusing on the context.
{PROMPTS["rag_response"]}
"""
    if mode in ["local", "global", "hybrid", "mix"]:
        global_config = asdict(rag)
        hl_keywords, ll_keywords = await extract_keywords_only(
            query, param, global_config, rag.llm_response_cache
        )
        # Add the keywords to the query parameters
        param.hl_keywords = _combine_keywords(param.hl_keywords, hl_keywords)
        param.ll_keywords = _combine_keywords(param.ll_keywords, ll_keywords)
        query = query.strip()
        (
            context,
            args_hash,
            quantized,
            min_val,
            max_val,
            entities_context,
            relations_context,
            text_units_context,
        ) = await prepare_context(
            query,
            rag.chunk_entity_relation_graph,
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.text_chunks,
            param,
            global_config,
            hashing_kv=rag.llm_response_cache,
            chunks_vdb=rag.chunks_vdb,
        )
        response = await extended_kg_query(
            query,
            context,
            param,
            global_config,
            args_hash,
            quantized,
            min_val,
            max_val,
            rag.llm_response_cache,
            system_prompt,
        )
        return ChatResponse(
            question=query,
            response=response,
            context=(
                context
                if query_params.include_context and query_params.include_context_as_text
                else None
            ),
            entities_context=entities_context if query_params.include_context else None,
            relations_context=(
                relations_context if query_params.include_context else None
            ),
            text_units_context=(
                text_units_context if query_params.include_context else None
            ),
        )
    return ChatResponse(
        question=query,
        response=await rag.aquery(query, param),
    )


# Copied from LightRAG
# from lightrag.operate import kg_query
async def prepare_context(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    chunks_vdb: BaseVectorStorage = None,
) -> tuple[str, str, np.ndarray | None, int, int, list[dict], list[dict], list[dict]]:

    # Handle cache
    args_hash = compute_args_hash(query_param.mode, query, cache_type="query")
    cached_response, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, query, query_param.mode, cache_type="query"
    )
    if cached_response is not None:
        return cached_response

    hl_keywords, ll_keywords = await get_keywords_from_query(
        query, query_param, global_config, hashing_kv
    )

    # Handle empty keywords
    if hl_keywords == [] and ll_keywords == []:
        logger.warning("low_level_keywords and high_level_keywords is empty")
        return PROMPTS["fail_response"]
    if ll_keywords == [] and query_param.mode in ["local", "hybrid"]:
        logger.warning(
            "low_level_keywords is empty, switching from %s mode to global mode",
            query_param.mode,
        )
        query_param.mode = "global"
    if hl_keywords == [] and query_param.mode in ["global", "hybrid"]:
        logger.warning(
            "high_level_keywords is empty, switching from %s mode to local mode",
            query_param.mode,
        )
        query_param.mode = "local"

    ll_keywords_str = ", ".join(ll_keywords) if ll_keywords else ""
    hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""

    # Build context
    entities_context, relations_context, text_units_context = (
        await _build_query_context(
            ll_keywords_str,
            hl_keywords_str,
            knowledge_graph_inst,
            entities_vdb,
            relationships_vdb,
            text_chunks_db,
            query_param,
            chunks_vdb,
        )
    )
    context = _build_context_str(
        entities_context, relations_context, text_units_context
    )
    return (
        context,
        args_hash,
        quantized,
        min_val,
        max_val,
        entities_context,
        relations_context,
        text_units_context,
    )


async def _build_query_context(
    ll_keywords: str,
    hl_keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    chunks_vdb: BaseVectorStorage = None,  # Add chunks_vdb parameter for mix mode
) -> tuple[list[dict], list[dict], list[dict]]:
    logger.info(f"Process {os.getpid()} building query context...")

    # Handle local and global modes as before
    if query_param.mode == "local":
        entities_context, relations_context, text_units_context = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )
    elif query_param.mode == "global":
        entities_context, relations_context, text_units_context = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            text_chunks_db,
            query_param,
        )
    else:  # hybrid or mix mode
        ll_data = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )
        hl_data = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            text_chunks_db,
            query_param,
        )

        (
            ll_entities_context,
            ll_relations_context,
            ll_text_units_context,
        ) = ll_data

        (
            hl_entities_context,
            hl_relations_context,
            hl_text_units_context,
        ) = hl_data

        # Initialize vector data with empty lists
        vector_entities_context, vector_relations_context, vector_text_units_context = (
            [],
            [],
            [],
        )

        # Only get vector data if in mix mode
        if query_param.mode == "mix" and hasattr(query_param, "original_query"):
            # Get tokenizer from text_chunks_db
            tokenizer = text_chunks_db.global_config.get("tokenizer")

            # Get vector context in triple format
            vector_data = await _get_vector_context(
                query_param.original_query,  # We need to pass the original query
                chunks_vdb,
                query_param,
                tokenizer,
            )

            # If vector_data is not None, unpack it
            if vector_data is not None:
                (
                    vector_entities_context,
                    vector_relations_context,
                    vector_text_units_context,
                ) = vector_data

        # Combine and deduplicate the entities, relationships, and sources
        entities_context = process_combine_contexts(
            hl_entities_context, ll_entities_context, vector_entities_context
        )
        relations_context = process_combine_contexts(
            hl_relations_context, ll_relations_context, vector_relations_context
        )
        text_units_context = process_combine_contexts(
            hl_text_units_context, ll_text_units_context, vector_text_units_context
        )
    # not necessary to use LLM to generate a response
    if not entities_context and not relations_context:
        return None

    return entities_context, relations_context, text_units_context


def _build_context_str(
    entities_context: list[dict],
    relations_context: list[dict],
    text_units_context: list[dict],
) -> str:
    entities_str = json.dumps(entities_context, ensure_ascii=False)
    relations_str = json.dumps(relations_context, ensure_ascii=False)
    text_units_str = json.dumps(text_units_context, ensure_ascii=False)

    result = f"""-----Entities(KG)-----

```json
{entities_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
{text_units_str}
```

"""
    return result


# Copied from LightRAG
# from lightrag.operate import kg_query
async def extended_kg_query(
    query: str,
    context: str,
    query_param: QueryParam,
    global_config: dict[str, str],
    args_hash: str,
    quantized: np.ndarray | None,
    min_val: int,
    max_val: int,
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
) -> str | AsyncIterator[str]:

    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)

    if query_param.only_need_context:
        return context
    if context is None:
        return PROMPTS["fail_response"]

    # Process conversation history
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    # Build system prompt
    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    sys_prompt_temp = system_prompt if system_prompt else PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data=context,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
    )

    if query_param.only_need_prompt:
        return sys_prompt

    response = await use_model_func(
        query,
        system_prompt=sys_prompt,
        stream=query_param.stream,
    )
    if isinstance(response, str) and len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )

    if hashing_kv.global_config.get("enable_llm_cache"):
        # Save to cache
        await save_to_cache(
            hashing_kv,
            CacheData(
                args_hash=args_hash,
                content=response,
                prompt=query,
                quantized=quantized,
                min_val=min_val,
                max_val=max_val,
                mode=query_param.mode,
                cache_type="query",
            ),
        )

    return response

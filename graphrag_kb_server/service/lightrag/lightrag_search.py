import time
import re
from pathlib import Path
from dataclasses import asdict
from typing import AsyncIterator
from functools import partial
import json
import os
import numpy as np
from pydantic import BaseModel

from lightrag import LightRAG, QueryParam
from lightrag.constants import (
    DEFAULT_MAX_ENTITY_TOKENS,
    DEFAULT_MAX_RELATION_TOKENS,
    DEFAULT_MAX_TOTAL_TOKENS,
    GRAPH_FIELD_SEP,
)
from lightrag.utils import truncate_list_by_token_size, process_chunks_unified

from lightrag.operate import (
    PROMPTS,
    extract_keywords_only,
    get_keywords_from_query,
    handle_cache,
    save_to_cache,
    CacheData,
    compute_args_hash,
    get_conversation_turns,
    _get_node_data,
    _get_edge_data,
    _get_vector_context,
)
from lightrag.base import BaseGraphStorage, BaseVectorStorage, BaseKVStorage
from lightrag.operate import (
    _find_most_related_text_unit_from_entities,
    _find_related_text_unit_from_relationships,
)

from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.model.rag_parameters import (
    QueryParameters,
    convert_to_lightrag_query_params,
)
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.model.rag_parameters import ContextFormat


def _combine_keywords(old_keywords: list[str], new_keywords: list[str]) -> list[str]:
    return list(set(old_keywords + new_keywords))


def _inject_keywords(query: str, hl_keywords: list[str], ll_keywords: list[str]) -> str:
    hl_keywords_str = "\n-".join(hl_keywords)
    ll_keywords_str = "\n-".join(ll_keywords)
    query = re.sub(
        r"<high_level_keywords>\s+?</high_level_keywords>",
        f"<high_level_keywords>{hl_keywords_str}</high_level_keywords>",
        query,
        flags=re.DOTALL,
    )
    return re.sub(
        r"<low_level_keywords>\s+?</low_level_keywords>",
        f"<low_level_keywords>{ll_keywords_str}</low_level_keywords>",
        query,
        flags=re.DOTALL,
    )


PROMPTS[
    "rag_response"
] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.


---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

When handling relationships with timestamps:
1. Each relationship has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting relationships, consider both the semantic content and the timestamp
3. Don't automatically prefer the most recently created relationships - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- List up to 10 most important reference sources at the end under "References" section. Clearly indicating whether each source is from Knowledge Graph (KG) or Document Chunks (DC), and include the file path if available, in the following format: [KG/DC] file_path
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Addtional user prompt: {user_prompt}

Response:"""

PROMPTS["document-retrieval"] = "\n".join(
    [
        line
        for line in PROMPTS["rag_response"].split("\n")
        if not line.strip().startswith(
            "- List up to 10 most important reference sources"
        )
    ]
)


async def extract_keywords_only_lightrag(
    text: str, param: QueryParam, project_folder: Path
) -> tuple[list[str], list[str]]:
    rag: LightRAG = await initialize_rag(project_folder)
    global_config = asdict(rag)
    return await extract_keywords_only(
        text, param, global_config, rag.llm_response_cache
    )


async def lightrag_search(
    query_params: QueryParameters,
    only_need_context: bool = False,
) -> ChatResponse:
    project_folder = query_params.context_params.project_dir
    query = query_params.context_params.query
    system_prompt_additional = query_params.system_prompt_additional or ""
    rag: LightRAG = await initialize_rag(project_folder)
    param = convert_to_lightrag_query_params(query_params, only_need_context)
    if query_params.system_prompt:
        system_prompt = query_params.system_prompt
    else:
        system_prompt = f"""{system_prompt_additional}

In case of a coloquial question or non context related sentence you can respond to it without focusing on the context.
{PROMPTS["rag_response"]}
"""
    if param.mode in ["local", "global", "hybrid", "mix"]:
        global_config = asdict(rag)
        param.conversation_history = [
            h for h in param.conversation_history if h.get("role") is not None
        ]
        param.history_turns = 1
        hl_keywords, ll_keywords = await extract_keywords_only(
            query, param, global_config, rag.llm_response_cache
        )
        # Add the keywords to the query parameters
        param.hl_keywords = _combine_keywords(param.hl_keywords, hl_keywords)
        param.ll_keywords = _combine_keywords(param.ll_keywords, ll_keywords)
        if query_params.callback is not None:
            await query_params.callback.callback(
                f"High level keywords: {"<SEP>".join(param.hl_keywords)}"
            )
            await query_params.callback.callback(
                f"Low level keywords: {"<SEP>".join(param.ll_keywords)}"
            )
        query = _inject_keywords(query, param.hl_keywords, param.ll_keywords)
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
            max_filepath_depth=query_params.max_filepath_depth,
            is_search_query=query_params.is_search_query,
            max_entity_size=query_params.max_entity_size,
            max_relation_size=query_params.max_relation_size,
            existing_hl_keywords=param.hl_keywords,
            existing_ll_keywords=param.ll_keywords,
        )
        if query_params.callback is not None:
            await query_params.callback.callback(
                f"Retrieved overall context with {len(entities_context)} entities and {len(relations_context)} relations and {len(text_units_context)} text units"
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
            structured_output=query_params.structured_output,
            structured_output_format=query_params.structured_output_format,
        )
        include_context_data = (
            query_params.context_format == ContextFormat.JSON
            or query_params.context_format == ContextFormat.JSON_STRING_WITH_JSON
        )
        return ChatResponse(
            question=query,
            response=response,
            context=(
                context
                if (
                    query_params.context_format == ContextFormat.JSON_STRING_WITH_JSON
                    or query_params.context_format == ContextFormat.JSON_STRING
                )
                or only_need_context
                else None
            ),
            entities_context=entities_context if include_context_data else None,
            relations_context=(relations_context if include_context_data else None),
            text_units_context=(text_units_context if include_context_data else None),
            hl_keywords=hl_keywords if query_params.keywords else None,
            ll_keywords=ll_keywords if query_params.keywords else None,
        )
    return ChatResponse(
        question=query,
        response=await rag.aquery(query, param),
    )


def _shorten_file_path(context_obj: dict, max_depth: int = 20) -> str:
    return [
        {**e, "file_path": "<SEP>".join(e["file_path"].split("<SEP>")[:max_depth])}
        for e in context_obj
    ]


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
    max_filepath_depth: int = 20,
    is_search_query: bool = False,
    max_entity_size: int = 1000,
    max_relation_size: int = 1000,
    existing_hl_keywords: list[str] = [],
    existing_ll_keywords: list[str] = [],
) -> tuple[str, str, np.ndarray | None, int, int, list[dict], list[dict], list[dict]]:

    # Handle cache
    cache_type = "query"
    args_hash = compute_args_hash(query_param.mode, query, cache_type)
    _, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, query, query_param.mode, cache_type="query"
    )

    if len(existing_hl_keywords) == 0 and len(existing_ll_keywords) == 0:
        hl_keywords, ll_keywords = await get_keywords_from_query(
            query, query_param, global_config, hashing_kv
        )
    else:
        hl_keywords = existing_hl_keywords
        ll_keywords = existing_ll_keywords

    # Handle empty keywords
    if hl_keywords == [] and ll_keywords == []:
        logger.warning("low_level_keywords and high_level_keywords is empty")
        return (
            PROMPTS["fail_response"],
            args_hash,
            quantized,
            min_val,
            max_val,
            [],
            [],
            [],
        )
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
    context_data = await _build_query_context(
        query,
        ll_keywords_str,
        hl_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        relationships_vdb,
        text_chunks_db,
        query_param,
        chunks_vdb,
    )

    if context_data is None:
        return (
            PROMPTS["fail_response"],
            args_hash,
            quantized,
            min_val,
            max_val,
            [],
            [],
            [],
        )
    entities_context, relations_context, text_units_context = context_data

    entities_context = _shorten_file_path(entities_context, max_filepath_depth)
    relations_context = _shorten_file_path(relations_context, max_filepath_depth)

    if is_search_query:
        entities_context = entities_context[:max_entity_size]
        relations_context = relations_context[:max_relation_size]

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
    query: str,
    ll_keywords: str,
    hl_keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    chunks_vdb: BaseVectorStorage = None,
):
    logger.info(f"Process {os.getpid()} building query context...")

    # Collect chunks from different sources separately
    vector_chunks = []
    entity_chunks = []
    relation_chunks = []
    entities_context = []
    relations_context = []

    # Store original data for later text chunk retrieval
    local_entities = []
    local_relations = []
    global_entities = []
    global_relations = []

    # Handle local and global modes
    if query_param.mode == "local":
        local_entities, local_relations = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
        )

    elif query_param.mode == "global":
        global_relations, global_entities = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
        )

    else:  # hybrid or mix mode
        local_entities, local_relations = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
        )
        global_relations, global_entities = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
        )

        # Get vector chunks first if in mix mode
        if query_param.mode == "mix" and chunks_vdb:
            vector_chunks = await _get_vector_context(
                query,
                chunks_vdb,
                query_param,
            )

    # Use round-robin merge to combine local and global data fairly
    final_entities = []
    seen_entities = set()

    # Round-robin merge entities
    max_len = max(len(local_entities), len(global_entities))
    for i in range(max_len):
        # First from local
        if i < len(local_entities):
            entity = local_entities[i]
            entity_name = entity.get("entity_name")
            if entity_name and entity_name not in seen_entities:
                final_entities.append(entity)
                seen_entities.add(entity_name)

        # Then from global
        if i < len(global_entities):
            entity = global_entities[i]
            entity_name = entity.get("entity_name")
            if entity_name and entity_name not in seen_entities:
                final_entities.append(entity)
                seen_entities.add(entity_name)

    # Round-robin merge relations
    final_relations = []
    seen_relations = set()

    max_len = max(len(local_relations), len(global_relations))
    for i in range(max_len):
        # First from local
        if i < len(local_relations):
            relation = local_relations[i]
            # Build relation unique identifier
            if "src_tgt" in relation:
                rel_key = tuple(sorted(relation["src_tgt"]))
            else:
                rel_key = tuple(
                    sorted([relation.get("src_id"), relation.get("tgt_id")])
                )

            if rel_key not in seen_relations:
                final_relations.append(relation)
                seen_relations.add(rel_key)

        # Then from global
        if i < len(global_relations):
            relation = global_relations[i]
            # Build relation unique identifier
            if "src_tgt" in relation:
                rel_key = tuple(sorted(relation["src_tgt"]))
            else:
                rel_key = tuple(
                    sorted([relation.get("src_id"), relation.get("tgt_id")])
                )

            if rel_key not in seen_relations:
                final_relations.append(relation)
                seen_relations.add(rel_key)

    # Generate entities context
    entities_context = []
    for i, n in enumerate(final_entities):
        created_at = n.get("created_at", "UNKNOWN")
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from node data
        file_path = n.get("file_path", "unknown_source")

        entities_context.append(
            {
                "id": i + 1,
                "entity": n["entity_name"],
                "type": n.get("entity_type", "UNKNOWN"),
                "description": n.get("description", "UNKNOWN"),
                "created_at": created_at,
                "file_path": file_path,
            }
        )

    # Generate relations context
    relations_context = []
    for i, e in enumerate(final_relations):
        created_at = e.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from edge data
        file_path = e.get("file_path", "unknown_source")

        # Handle different relation data formats
        if "src_tgt" in e:
            entity1, entity2 = e["src_tgt"]
        else:
            entity1, entity2 = e.get("src_id"), e.get("tgt_id")

        relations_context.append(
            {
                "id": i + 1,
                "entity1": entity1,
                "entity2": entity2,
                "description": e.get("description", "UNKNOWN"),
                "created_at": created_at,
                "file_path": file_path,
            }
        )

    logger.debug(
        f"Initial KG query results: {len(entities_context)} entities, {len(relations_context)} relations"
    )

    # Unified token control system - Apply precise token limits to entities and relations
    tokenizer = text_chunks_db.global_config.get("tokenizer")
    # Get new token limits from query_param (with fallback to global_config)
    max_entity_tokens = getattr(
        query_param,
        "max_entity_tokens",
        text_chunks_db.global_config.get(
            "max_entity_tokens", DEFAULT_MAX_ENTITY_TOKENS
        ),
    )
    max_relation_tokens = getattr(
        query_param,
        "max_relation_tokens",
        text_chunks_db.global_config.get(
            "max_relation_tokens", DEFAULT_MAX_RELATION_TOKENS
        ),
    )
    max_total_tokens = getattr(
        query_param,
        "max_total_tokens",
        text_chunks_db.global_config.get("max_total_tokens", DEFAULT_MAX_TOTAL_TOKENS),
    )

    # Truncate entities based on complete JSON serialization
    if entities_context:
        # Process entities context to replace GRAPH_FIELD_SEP with : in file_path fields
        for entity in entities_context:
            if "file_path" in entity and entity["file_path"]:
                entity["file_path"] = entity["file_path"].replace(GRAPH_FIELD_SEP, ";")

        entities_context = truncate_list_by_token_size(
            entities_context,
            key=lambda x: json.dumps(x, ensure_ascii=False),
            max_token_size=max_entity_tokens,
            tokenizer=tokenizer,
        )

    # Truncate relations based on complete JSON serialization
    if relations_context:
        # Process relations context to replace GRAPH_FIELD_SEP with : in file_path fields
        for relation in relations_context:
            if "file_path" in relation and relation["file_path"]:
                relation["file_path"] = relation["file_path"].replace(
                    GRAPH_FIELD_SEP, ";"
                )

        relations_context = truncate_list_by_token_size(
            relations_context,
            key=lambda x: json.dumps(x, ensure_ascii=False),
            max_token_size=max_relation_tokens,
            tokenizer=tokenizer,
        )

    # After truncation, get text chunks based on final entities and relations
    logger.info(
        f"Truncated KG query results: {len(entities_context)} entities, {len(relations_context)} relations"
    )

    # Create filtered data based on truncated context
    final_node_datas = []
    if entities_context and final_entities:
        final_entity_names = {e["entity"] for e in entities_context}
        seen_nodes = set()
        for node in final_entities:
            name = node.get("entity_name")
            if name in final_entity_names and name not in seen_nodes:
                final_node_datas.append(node)
                seen_nodes.add(name)

    final_edge_datas = []
    if relations_context and final_relations:
        final_relation_pairs = {(r["entity1"], r["entity2"]) for r in relations_context}
        seen_edges = set()
        for edge in final_relations:
            src, tgt = edge.get("src_id"), edge.get("tgt_id")
            if src is None or tgt is None:
                src, tgt = edge.get("src_tgt", (None, None))

            pair = (src, tgt)
            if pair in final_relation_pairs and pair not in seen_edges:
                final_edge_datas.append(edge)
                seen_edges.add(pair)

    # Get text chunks based on final filtered data
    if final_node_datas:
        entity_chunks = await _find_most_related_text_unit_from_entities(
            final_node_datas,
            query_param,
            text_chunks_db,
            knowledge_graph_inst,
        )

    if final_edge_datas:
        relation_chunks = await _find_related_text_unit_from_relationships(
            final_edge_datas,
            query_param,
            text_chunks_db,
            entity_chunks,
        )

    # Round-robin merge chunks from different sources with deduplication by chunk_id
    merged_chunks = []
    seen_chunk_ids = set()
    max_len = max(len(vector_chunks), len(entity_chunks), len(relation_chunks))
    origin_len = len(vector_chunks) + len(entity_chunks) + len(relation_chunks)

    for i in range(max_len):
        # Add from vector chunks first (Naive mode)
        if i < len(vector_chunks):
            chunk = vector_chunks[i]
            chunk_id = chunk.get("chunk_id") or chunk.get("id")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                merged_chunks.append(
                    {
                        "content": chunk["content"],
                        "file_path": chunk.get("file_path", "unknown_source"),
                    }
                )

        # Add from entity chunks (Local mode)
        if i < len(entity_chunks):
            chunk = entity_chunks[i]
            chunk_id = chunk.get("chunk_id") or chunk.get("id")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                merged_chunks.append(
                    {
                        "content": chunk["content"],
                        "file_path": chunk.get("file_path", "unknown_source"),
                    }
                )

        # Add from relation chunks (Global mode)
        if i < len(relation_chunks):
            chunk = relation_chunks[i]
            chunk_id = chunk.get("chunk_id") or chunk.get("id")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                merged_chunks.append(
                    {
                        "content": chunk["content"],
                        "file_path": chunk.get("file_path", "unknown_source"),
                    }
                )

    logger.debug(
        f"Round-robin merged total chunks from {origin_len} to {len(merged_chunks)}"
    )

    # Apply token processing to merged chunks
    text_units_context = []
    if merged_chunks:
        # Calculate dynamic token limit for text chunks
        entities_str = json.dumps(entities_context, ensure_ascii=False)
        relations_str = json.dumps(relations_context, ensure_ascii=False)

        # Calculate base context tokens (entities + relations + template)
        kg_context_template = """-----Entities(KG)-----

```json
{entities_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
[]
```

"""
        kg_context = kg_context_template.format(
            entities_str=entities_str, relations_str=relations_str
        )
        kg_context_tokens = len(tokenizer.encode(kg_context))

        # Calculate actual system prompt overhead dynamically
        # 1. Calculate conversation history tokens
        history_context = ""
        if query_param.conversation_history:
            history_context = get_conversation_turns(
                query_param.conversation_history, query_param.history_turns
            )
        history_tokens = (
            len(tokenizer.encode(history_context)) if history_context else 0
        )

        # 2. Calculate system prompt template tokens (excluding context_data)
        user_prompt = query_param.user_prompt if query_param.user_prompt else ""
        response_type = (
            query_param.response_type
            if query_param.response_type
            else "Multiple Paragraphs"
        )

        # Get the system prompt template from PROMPTS
        sys_prompt_template = text_chunks_db.global_config.get(
            "system_prompt_template", PROMPTS["rag_response"]
        )

        # Create a sample system prompt with placeholders filled (excluding context_data)
        sample_sys_prompt = sys_prompt_template.format(
            history=history_context,
            context_data="",  # Empty for overhead calculation
            response_type=response_type,
            user_prompt=user_prompt,
        )
        sys_prompt_template_tokens = len(tokenizer.encode(sample_sys_prompt))

        # Total system prompt overhead = template + query tokens
        query_tokens = len(tokenizer.encode(query))
        sys_prompt_overhead = sys_prompt_template_tokens + query_tokens

        buffer_tokens = 100  # Safety buffer as requested

        # Calculate available tokens for text chunks
        used_tokens = kg_context_tokens + sys_prompt_overhead + buffer_tokens
        available_chunk_tokens = max_total_tokens - used_tokens

        logger.debug(
            f"Token allocation - Total: {max_total_tokens}, History: {history_tokens}, SysPrompt: {sys_prompt_overhead}, KG: {kg_context_tokens}, Buffer: {buffer_tokens}, Available for chunks: {available_chunk_tokens}"
        )

        # Apply token truncation to chunks using the dynamic limit
        truncated_chunks = await process_chunks_unified(
            query=query,
            unique_chunks=merged_chunks,
            query_param=query_param,
            global_config=text_chunks_db.global_config,
            source_type=query_param.mode,
            chunk_token_limit=available_chunk_tokens,  # Pass dynamic limit
        )

        # Rebuild text_units_context with truncated chunks
        for i, chunk in enumerate(truncated_chunks):
            text_units_context.append(
                {
                    "id": i + 1,
                    "content": chunk["content"],
                    "file_path": chunk.get("file_path", "unknown_source"),
                }
            )

        logger.debug(
            f"Final chunk processing: {len(merged_chunks)} -> {len(text_units_context)} (chunk available tokens: {available_chunk_tokens})"
        )

    logger.info(
        f"Final context: {len(entities_context)} entities, {len(relations_context)} relations, {len(text_units_context)} chunks"
    )

    # not necessary to use LLM to generate a response
    if not entities_context and not relations_context:
        return None

    return entities_context, relations_context, text_units_context


def process_combine_contexts(*context_lists):
    """
    Combine multiple context lists and remove duplicate content

    Args:
        *context_lists: Any number of context lists

    Returns:
        Combined context list with duplicates removed
    """
    seen_content = {}
    combined_data = []

    # Iterate through all input context lists
    for context_list in context_lists:
        if not context_list:  # Skip empty lists
            continue
        for item in context_list:
            content_dict = {
                k: v for k, v in item.items() if k != "id" and k != "created_at"
            }
            content_key = tuple(sorted(content_dict.items()))
            if content_key not in seen_content:
                seen_content[content_key] = item
                combined_data.append(item)

    # Reassign IDs
    for i, item in enumerate(combined_data):
        item["id"] = str(i + 1)

    return combined_data


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
    context: str | None,
    query_param: QueryParam,
    global_config: dict[str, str],
    args_hash: str,
    quantized: np.ndarray | None,
    min_val: int,
    max_val: int,
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    structured_output: bool = False,
    structured_output_format: BaseModel | None = None,
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
        structured_output=structured_output,
        structured_output_format=structured_output_format,
    )
    expand_files(response)

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


def expand_files(response: dict[str, any] | str) -> None:
    """
    Expands file references in the response by splitting files separated by '<SEP>'.

    Args:
        response: Response dictionary containing references or a string (ignored)

    Modifies:
        response: Updates the 'references' key with expanded file references
    """
    final_references = {}
    if isinstance(response, str) or "references" not in response:
        return
    for reference in response["references"]:
        file_content = reference.get("file", None)
        type = reference.get("type", None)
        main_keyword = reference.get("main_keyword", None)
        if file_content is not None:
            files = file_content.split("<SEP>")
            for file in files:
                final_references[file] = {
                    "file": file,
                    "type": type,
                    "main_keyword": main_keyword,
                }

    response["references"] = list(final_references.values())


if __name__ == "__main__":
    print(PROMPTS["document-retrieval"])

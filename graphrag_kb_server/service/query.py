from pathlib import Path
from typing import Tuple, Union
import tiktoken

import pandas as pd

from graphrag_kb_server.model.rag_parameters import ContextParameters

from graphrag.model import CommunityReport, Entity
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_relationships,
    read_indexer_covariates,
    read_indexer_text_units,
)
from graphrag.query.input.loaders.dfs import (
    store_entity_semantic_embeddings,
)
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.llm.oai.typing import OpenaiApiType
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from markdown import markdown

from graphrag_kb_server.config import cfg
from graphrag_kb_server.service.index import DIR_VECTOR_DB

ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
COMMUNITY_REPORT_TABLE = "create_final_community_reports"
RELATIONSHIP_TABLE = "create_final_relationships"
TEXT_UNIT_TABLE = "create_final_text_units"
COVARIATE_TABLE = "create_final_covariates"

# community level in the Leiden community hierarchy from which we will load the community reports
# higher value means we use reports from more fine-grained communities (at the cost of higher computation cost)
COMMUNITY_LEVEL = 2

token_encoder = tiktoken.get_encoding("cl100k_base")


def load_project_data(
    project_dir: Path, default_entity_description_table_df: pd.DataFrame
) -> Tuple[list[CommunityReport], list[Entity]]:
    entity_df = pd.read_parquet(f"{project_dir}/output/{ENTITY_TABLE}.parquet")
    entity_embedding_df = pd.read_parquet(
        f"{project_dir}/output/{ENTITY_EMBEDDING_TABLE}.parquet"
    )
    report_df = pd.read_parquet(
        f"{project_dir}/output/{COMMUNITY_REPORT_TABLE}.parquet"
    )

    entity_embedding_df["description_embedding"] = default_entity_description_table_df[
        "vector"
    ].copy()
    reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
    entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)

    return reports, entities


def init_local_params(context_parameters: ContextParameters) -> Tuple[dict, dict]:
    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
        "max_tokens": context_parameters.context_size,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    }

    llm_params = {
        "max_tokens": 2_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000=1500)
        "temperature": 0.0,
    }
    return (local_context_params, llm_params)


def get_claims(project_dir: Path) -> Union[dict, None]:
    file = f"{project_dir}/output/{COVARIATE_TABLE}.parquet"
    if Path(file).exists():
        covariate_df = pd.read_parquet(file)
        claims = read_indexer_covariates(covariate_df)
        covariates = {"claims": claims}
        return covariates
    return None


def prepare_vector_store() -> Tuple[LanceDBVectorStore, pd.DataFrame]:
    # load description embeddings to an in-memory lancedb vectorstore
    # to connect to a remote db, specify url and port values.
    description_embedding_store = LanceDBVectorStore(
        collection_name="entity_description_embeddings",
    )
    description_embedding_store.connect(db_uri=DIR_VECTOR_DB)
    default_entity_description_table = description_embedding_store.db_connection[
        "default-entity-description"
    ]
    default_entity_description_table_df = default_entity_description_table.to_pandas()
    return description_embedding_store, default_entity_description_table_df


def build_local_context_builder(project_dir: Path) -> LocalSearchMixedContext:

    description_embedding_store, default_entity_description_table_df = (
        prepare_vector_store()
    )

    reports, entities = load_project_data(
        project_dir, default_entity_description_table_df
    )

    store_entity_semantic_embeddings(
        entities=entities, vectorstore=description_embedding_store
    )

    relationship_df = pd.read_parquet(
        f"{project_dir}/output/{RELATIONSHIP_TABLE}.parquet"
    )
    relationships = read_indexer_relationships(relationship_df)

    covariates = get_claims(project_dir)

    text_unit_df = pd.read_parquet(f"{project_dir}/output/{TEXT_UNIT_TABLE}.parquet")
    text_units = read_indexer_text_units(text_unit_df)

    text_embedder = OpenAIEmbedding(
        api_key=cfg.openai_api_key,
        api_base=None,
        api_type=OpenaiApiType.OpenAI,
        model=cfg.openai_api_model_embedding,
        deployment_name=cfg.openai_api_model_embedding,
        max_retries=20,
    )

    return LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        # if you did not run covariates during indexing, set this to None
        covariates=covariates,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )


def build_global_context_builder(project_dir: Path) -> GlobalCommunityContext:

    _, default_entity_description_table_df = prepare_vector_store()

    reports, entities = load_project_data(
        project_dir, default_entity_description_table_df
    )

    return GlobalCommunityContext(
        community_reports=reports,
        entities=entities,  # default to None if you don't want to use community weights for ranking
        token_encoder=token_encoder,
    )


def prepare_local_search(context_parameters: ContextParameters) -> LocalSearch:
    context_builder = build_local_context_builder(context_parameters.project_dir)

    local_context_params, llm_params = init_local_params(context_parameters)

    return LocalSearch(
        llm=cfg.llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
        response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
    )


async def rag_local(context_parameters: ContextParameters) -> str:

    search_engine = prepare_local_search(context_parameters)

    result = await search_engine.asearch(context_parameters.query)
    return markdown(result.response)


def rag_local_build_context(context_parameters: ContextParameters) -> Tuple[str, dict]:

    search_engine = prepare_local_search(context_parameters)
    context_text, context_records = search_engine.context_builder.build_context(
        query=context_parameters.query,
        conversation_history=None,
        **search_engine.context_builder_params,
    )
    return context_text, context_records


def prepare_global_search(context_parameters: ContextParameters) -> GlobalSearch:
    context_builder = build_global_context_builder(context_parameters.project_dir)

    context_builder_params = {
        "use_community_summary": False,  # False means using full community reports. True means using community short summaries.
        "shuffle_data": True,
        "include_community_rank": True,
        "min_community_rank": 0,
        "community_rank_name": "rank",
        "include_community_weight": True,
        "community_weight_name": "occurrence weight",
        "normalize_community_weight": True,
        "max_tokens": context_parameters.context_size,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
        "context_name": "Reports",
    }

    map_llm_params = {
        "max_tokens": 1000,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    reduce_llm_params = {
        "max_tokens": 2000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000-1500)
        "temperature": 0.0,
    }

    return GlobalSearch(
        llm=cfg.llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        max_data_tokens=12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,  # set this to True will add instruction to encourage the LLM to incorporate general knowledge in the response, which may increase hallucinations, but could be useful in some use cases.
        json_mode=True,  # set this to False if your LLM model does not support JSON mode.
        context_builder_params=context_builder_params,
        concurrent_coroutines=32,
        response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
    )


def rag_global_build_context(context_parameters: ContextParameters) -> Tuple[str, dict]:

    global_search: GlobalSearch = prepare_global_search(context_parameters)

    context_text, context_records = global_search.context_builder.build_context(
        query=context_parameters.query,
        conversation_history=None,
        **global_search.context_builder_params,
    )
    context_str = ""
    if isinstance(context_text, list):
        context_str = "\n".join(context_text)
    return context_str, context_records


def rag_combined_context(context_parameters: ContextParameters) -> Tuple[str, dict]:

    local_context_text, local_context_records = rag_local_build_context(
        context_parameters
    )
    global_context_text, global_context_records = rag_global_build_context(
        context_parameters
    )

    template = """
# LOCAL CONTEXT

{local_context_text}

# GLOBAL CONTEXT

{global_context_text}
"""
    context_text = template.format(
        local_context_text=local_context_text, global_context_text=global_context_text
    )
    context_records = {"local": local_context_records, "global": global_context_records}
    return context_text, context_records


async def rag_global(context_parameters: ContextParameters) -> str:

    search_engine = prepare_global_search(context_parameters)

    result = await search_engine.asearch(context_parameters.query)
    return markdown(result.response)

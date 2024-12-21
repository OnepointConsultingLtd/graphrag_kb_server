from pathlib import Path
from typing import Tuple, Union
import tiktoken

import pandas as pd

from graphrag_kb_server.model.rag_parameters import ContextParameters

from graphrag.model.entity import Entity
from graphrag.index.operations.summarize_communities.typing import CommunityReport
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_relationships,
    read_indexer_covariates,
    read_indexer_text_units,
    read_indexer_communities,
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
from graphrag.query.structured_search.base import SearchResult
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.drift_search.search import DRIFTSearch
from graphrag.vector_stores.base import BaseVectorStore, VectorStoreDocument
from graphrag.query.context_builder.builders import ContextBuilderResult
from graphrag.model.community import Community
from graphrag.query.indexer_adapters import embed_community_reports

from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.context import (
    ContextResult,
    Search,
    create_context_result,
    create_global_context_result,
)
from graphrag_kb_server.model.context_builder_data import ContextBuilderData
from graphrag.query.structured_search.drift_search.drift_context import (
    DRIFTSearchContextBuilder,
)

ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
COMMUNITY_REPORT_TABLE = "create_final_community_reports"
COMMUNITY_TABLE = "create_final_communities"
RELATIONSHIP_TABLE = "create_final_relationships"
TEXT_UNIT_TABLE = "create_final_text_units"
COVARIATE_TABLE = "create_final_covariates"

# community level in the Leiden community hierarchy from which we will load the community reports
# higher value means we use reports from more fine-grained communities (at the cost of higher computation cost)
COMMUNITY_LEVEL = 2

token_encoder = tiktoken.get_encoding("cl100k_base")


def load_project_data(
    project_dir: Path, default_entity_description_table_df: pd.DataFrame
) -> Tuple[list[CommunityReport], list[Entity], list[Community], OpenAIEmbedding]:
    output = f"{project_dir}/output"
    entity_df = pd.read_parquet(f"{output}/{ENTITY_TABLE}.parquet")
    entity_embedding_df = pd.read_parquet(f"{output}/{ENTITY_EMBEDDING_TABLE}.parquet")
    report_df = pd.read_parquet(f"{output}/{COMMUNITY_REPORT_TABLE}.parquet")
    text_embedder = create_text_embedder()
    embed_community_reports(
        report_df, text_embedder, embedding_col="full_content_embedding"
    )

    entity_embedding_df["description_embedding"] = default_entity_description_table_df[
        "vector"
    ].copy()

    reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
    entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)

    community_df = pd.read_parquet(f"{output}/{COMMUNITY_TABLE}.parquet")

    communities = read_indexer_communities(community_df, entity_df, report_df)

    return reports, entities, communities, text_embedder


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


def prepare_vector_store(project_dir: Path) -> Tuple[LanceDBVectorStore, pd.DataFrame]:
    # load description embeddings to an in-memory lancedb vectorstore
    # to connect to a remote db, specify url and port values.
    entity_description_table = "default-entity-description"
    description_embedding_store = LanceDBVectorStore(
        collection_name=entity_description_table,
    )
    description_embedding_store.connect(db_uri=project_dir / cfg.vector_db_dir)
    default_entity_description_table = description_embedding_store.db_connection[
        entity_description_table
    ]
    default_entity_description_table_df = default_entity_description_table.to_pandas()
    return description_embedding_store, default_entity_description_table_df


def store_entity_semantic_embeddings(
    entities: list[Entity],
    vectorstore: BaseVectorStore,
) -> BaseVectorStore:
    """Store entity semantic embeddings in a vectorstore."""
    documents = [
        VectorStoreDocument(
            id=entity.id,
            text=entity.description,
            vector=entity.description_embedding,
            attributes=(
                {"title": entity.title, **entity.attributes}
                if entity.attributes
                else {"title": entity.title}
            ),
        )
        for entity in entities
    ]
    vectorstore.load_documents(documents=documents)
    return vectorstore


def create_text_embedder() -> OpenAIEmbedding:
    return OpenAIEmbedding(
        api_key=cfg.openai_api_key,
        api_base=None,
        api_type=OpenaiApiType.OpenAI,
        model=cfg.openai_api_model_embedding,
        deployment_name=cfg.openai_api_model_embedding,
        max_retries=20,
    )


def create_context_builder_data(project_dir: Path) -> ContextBuilderData:
    description_embedding_store, default_entity_description_table_df = (
        prepare_vector_store(project_dir)
    )

    reports, entities, _communities, text_embedder = load_project_data(
        project_dir, default_entity_description_table_df
    )
    relationship_df = pd.read_parquet(
        f"{project_dir}/output/{RELATIONSHIP_TABLE}.parquet"
    )
    relationships = read_indexer_relationships(relationship_df)
    text_unit_df = pd.read_parquet(f"{project_dir}/output/{TEXT_UNIT_TABLE}.parquet")
    text_units = read_indexer_text_units(text_unit_df)
    covariates = get_claims(project_dir)

    return ContextBuilderData(
        text_embedder=text_embedder,
        reports=reports,
        entities=entities,
        relationships=relationships,
        text_units=text_units,
        covariates=covariates,
        description_embedding_store=description_embedding_store,
    )


def build_local_context_builder(project_dir: Path) -> LocalSearchMixedContext:

    context_builder_data = create_context_builder_data(project_dir)

    return LocalSearchMixedContext(
        community_reports=context_builder_data.reports,
        text_units=context_builder_data.text_units,
        entities=context_builder_data.entities,
        relationships=context_builder_data.relationships,
        # if you did not run covariates during indexing, set this to None
        covariates=context_builder_data.covariates,
        entity_text_embeddings=context_builder_data.description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
        text_embedder=context_builder_data.text_embedder,
        token_encoder=token_encoder,
    )


def build_global_context_builder(project_dir: Path) -> GlobalCommunityContext:

    _, default_entity_description_table_df = prepare_vector_store(project_dir)

    reports, entities, communities, _text_embedder = load_project_data(
        project_dir, default_entity_description_table_df
    )

    return GlobalCommunityContext(
        community_reports=reports,
        communities=communities,
        entities=entities,  # default to None if you don't want to use community weights for ranking
        token_encoder=token_encoder,
    )


def build_local_drift_context_builder(project_dir: Path) -> DRIFTSearchContextBuilder:

    context_builder_data = create_context_builder_data(project_dir)
    context_builder = DRIFTSearchContextBuilder(
        chat_llm=cfg.llm,
        text_embedder=context_builder_data.text_embedder,
        entities=context_builder_data.entities,
        relationships=context_builder_data.relationships,
        reports=context_builder_data.reports,
        entity_text_embeddings=context_builder_data.description_embedding_store,
        text_units=context_builder_data.text_units,
    )
    return context_builder


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


async def prepare_rag_drift(context_parameters: ContextParameters) -> SearchResult:
    context_builder = build_local_drift_context_builder(context_parameters.project_dir)
    search = DRIFTSearch(
        llm=cfg.llm, context_builder=context_builder, token_encoder=token_encoder
    )
    result = await search.asearch(context_parameters.query)
    return result


def rag_local_build_context(
    context_parameters: ContextParameters,
) -> ContextResult:

    search_engine = prepare_local_search(context_parameters)
    context_builder_result = search_engine.context_builder.build_context(
        query=context_parameters.query,
        conversation_history=None,
        **search_engine.context_builder_params,
    )
    return create_context_result(context_builder_result, Search.LOCAL)


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


async def rag_drift(context_parameters: ContextParameters) -> str:
    result = await prepare_rag_drift(context_parameters)
    response = result.response
    if (
        "nodes" in response
        and len(response["nodes"]) > 0
        and "answer" in response["nodes"][0]
    ):
        return response["nodes"][0]["answer"]
    return "Could not fetch content"


async def rag_local(context_parameters: ContextParameters) -> str:
    search_engine = prepare_local_search(context_parameters)
    result = await search_engine.asearch(context_parameters.query)
    return result.response


async def rag_global(context_parameters: ContextParameters) -> str:
    search_engine = prepare_global_search(context_parameters)
    result = await search_engine.asearch(context_parameters.query)
    return result.response


async def rag_global_build_context(
    context_parameters: ContextParameters,
) -> ContextResult:
    global_search: GlobalSearch = prepare_global_search(context_parameters)
    context_builder_result: ContextBuilderResult = (
        await global_search.context_builder.build_context(
            query=context_parameters.query,
            conversation_history=None,
            **global_search.context_builder_params,
        )
    )
    return create_context_result(context_builder_result, Search.GLOBAL)


async def rag_combined_context(
    context_parameters: ContextParameters,
) -> ContextResult:
    local_build_result = rag_local_build_context(context_parameters)
    global_build_result = await rag_global_build_context(context_parameters)
    return create_global_context_result(local_build_result, global_build_result)


async def rag_drift_context(context_parameters: ContextParameters) -> ContextResult:
    response = await prepare_rag_drift(context_parameters)
    questions = "\n".join([f"- {s}" for s in response.context_data.keys()])
    return ContextResult(
        context_text=questions, local_context_records={}, global_context_records={}
    )

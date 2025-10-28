from pathlib import Path
import asyncio

from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
)
from graphrag_kb_server.model.search.match_query import MatchOutput
from graphrag_kb_server.model.search.entity import Abstraction
from graphrag_kb_server.model.rag_parameters import QueryParameters, ContextParameters
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search, PROMPTS
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.model.search.search import (
    SummarisationRequestWithDocumentPath,
    SummarisationRequest,
    SummarisationResponse,
    SearchResults,
    RELEVANCE_SCORE_POINTS_MAP,
)
from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.callbacks.callback_support import BaseCallback
from graphrag_kb_server.logger import logger

DOCUMENT_PATHS_LIMIT = 10

SEPARATORS = ["<SEP>", ";"]


async def retrieve_relevant_documents(
    project_dir: Path, query: DocumentSearchQuery, callback: BaseCallback = None
) -> SearchResults:
    """
    Searches documents that are relevant to the query and summarizes them according to the user's profile and question.

    Args:
        project_dir: The directory of the project
        query: The query to search for documents

    Returns:
        A list of summarization responses with document paths
    """
    chat_response = await search_documents(project_dir, query, callback)
    documents = chat_response.response["documents"]
    if callback is not None:
        await callback.callback(chat_response.response["response"])
        logger.info(f"Answer prepared: {chat_response.response['response']}")
        await callback.callback(f"Extracted {len(documents)} references.")
        logger.info(f"Extracted {len(documents)} references")
    return SearchResults(
        request_id=query.request_id,
        documents=documents,
        response=chat_response.response["response"],
    )


async def search_documents(
    project_dir: Path, query: DocumentSearchQuery, callback: BaseCallback = None
) -> ChatResponse:
    question = generate_question(query)
    query_params = generate_query(project_dir, query, question, callback)
    retries = 5
    while retries > 0:
        try:
            results = await lightrag_search(query_params)
            results.response["documents"] = sorted(
                results.response["documents"],
                key=lambda r: RELEVANCE_SCORE_POINTS_MAP[r["relevancy_score"]],
                reverse=True,
            )
            return results
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            retries -= 1
            if retries == 0:
                raise e
            params = {
                **query_params.model_dump(),
                "max_entity_size": 10,
                "max_relation_size": 10,
                "max_filepath_depth": 10,
            }
            await callback.callback(
                f"Failed to search documents, retrying {retries} more times."
            )
            query_params = QueryParameters(**params)
            logger.info(f"Retrying {retries} times")


def get_document_text(project_dir: Path, document_path: Path) -> str:
    document_text = f"Source not found: {document_path}"
    if not document_path.is_file():
        return f"Source not found: {document_path}"
    if not document_path.exists():
        file_name = document_path.name
        similar_files = list(project_dir.rglob(f"**/{file_name}"))
        if len(similar_files) > 0:
            document_text = similar_files[0].read_text(encoding="utf-8")
        else:
            document_text = f"Source not found: {file_name}"
    else:
        document_text = document_path.read_text(encoding="utf-8")
    return document_text


async def summarize_document_with_document_path(
    project_dir: Path,
    request: SummarisationRequestWithDocumentPath,
) -> str:  #
    document_text = get_document_text(project_dir, Path(request.document_path))
    return await summarize_document(
        SummarisationRequest(
            user_profile=request.user_profile,
            question=request.question,
            document=document_text,
        )
    )


async def summarize_document(request: SummarisationRequest) -> SummarisationResponse:
    if request.question is None or len(request.question.strip()) == 0:
        user_prompt = prompts["document-summarization"]["human_prompt_question"].format(
            user_profile=request.user_profile,
            question=request.question,
            document=request.document,
        )
    else:
        user_prompt = prompts["document-summarization"][
            "human_prompt_no_question"
        ].format(
            user_profile=request.user_profile,
            document=request.document,
        )
    retries = 5
    while retries > 0:
        try:
            summarisation_response_dict = await structured_completion(
                prompts["document-summarization"]["system_prompt"],
                user_prompt,
                SummarisationResponse,
            )
            return SummarisationResponse(**summarisation_response_dict)
        except Exception as e:
            logger.error(f"Error summarizing document: {e}")
            retries -= 1
            if retries == 0:
                raise e


def generate_query(
    project_dir: Path,
    query: DocumentSearchQuery,
    question: str,
    callback: BaseCallback = None,
) -> QueryParameters:
    system_prompt_additional = prompts["document-retrieval"]["system_prompt_additional"]
    query_params = QueryParameters(
        format="json",
        search="hybrid",
        engine=Engine.LIGHTRAG,
        context_params=ContextParameters(
            query=question,
            project_dir=project_dir,
            context_size=8000,
        ),
        system_prompt=PROMPTS["document-retrieval"],
        system_prompt_additional=system_prompt_additional,
        hl_keywords=[
            entity.entity
            for entity_list in query.topics_of_interest.entity_dict.values()
            for entity in entity_list.entities
            if entity.abstraction == Abstraction.HIGH_LEVEL
        ],
        ll_keywords=[
            entity.entity
            for entity_list in query.topics_of_interest.entity_dict.values()
            for entity in entity_list.entities
            if entity.abstraction == Abstraction.LOW_LEVEL
        ],
        include_context=True,
        include_context_as_text=False,
        structured_output=True,
        structured_output_format=SearchResults,
        max_filepath_depth=query.max_filepath_depth,
        is_search_query=query.is_search_query,
        callback=callback,
    )
    return query_params


def generate_question(document_search_query: DocumentSearchQuery) -> str:
    template = prompts["document-retrieval"]["question-template"]

    def format_keywords(match_output: MatchOutput, high_level: bool) -> str:
        res = ""
        unique_keywords = set()
        for classification in match_output.entity_dict.values():
            for entity in classification.entities:
                if entity.entity in unique_keywords:
                    continue
                unique_keywords.add(entity.entity)
                if high_level and entity.abstraction == Abstraction.HIGH_LEVEL:
                    res += f"- {entity.entity}\n"
                else:
                    res += f"- {entity.entity}\n"
        return res

    high_level_keywords = format_keywords(
        document_search_query.topics_of_interest, high_level=True
    )
    low_level_keywords = format_keywords(
        document_search_query.topics_of_interest, high_level=False
    )
    user_profile = document_search_query.user_profile
    return template.format(
        high_level_keywords=high_level_keywords,
        low_level_keywords=low_level_keywords,
        user_profile=user_profile,
        question=(
            document_search_query.question if document_search_query.question else ""
        ),
    )


if __name__ == "__main__":
    from graphrag_kb_server.test.provider.search_provider import (
        create_document_search_query,
    )

    project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")

    def test_generate_query():
        document_search_query = create_document_search_query()
        query_params = generate_query(
            project_dir,
            document_search_query,
            "What are the main challenges in the field of AI?",
        )
        print(query_params)

    def test_search_documents():
        import asyncio

        chat_response = asyncio.run(
            search_documents(project_dir, create_document_search_query())
        )
        assert chat_response is not None, "No chat response returned"
        assert isinstance(
            chat_response, ChatResponse
        ), "Chat response is not a ChatResponse"
        print(chat_response)

    def test_get_document_text():
        document_text = get_document_text(
            project_dir,
            Path(
                "/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/input/clustre/Case studies/Case_Study_-_AIMIA_and_Zuhlke.txt"
            ),
        )
        print(document_text)
        document_text = get_document_text(
            project_dir,
            Path(
                "/var/graphrag/tennants/gil_fernandes/lightrag/clustre_2/input/clustre/Case studies/Case_Study_-_AIMIA_and_Zuhlke.txt"
            ),
        )
        print(document_text)

    def test_retrieve_relevant_documents():
        search_results = asyncio.run(
            retrieve_relevant_documents(project_dir, create_document_search_query())
        )
        print(search_results.response)
        for document in search_results.documents:
            print(document.summary)
            print(document.relevance)
            print(document.relevancy_score)
            print(document.document_path)

    # test_generate_query()
    # test_search_documents()
    # test_get_document_text()
    test_retrieve_relevant_documents()

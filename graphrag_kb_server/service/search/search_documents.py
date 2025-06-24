from pathlib import Path
import asyncio

from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
    SummarisationResponseWithDocument,
)
from graphrag_kb_server.model.search.match_query import MatchOutput
from graphrag_kb_server.model.search.entity import Abstraction
from graphrag_kb_server.model.rag_parameters import QueryParameters, ContextParameters
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.lightrag.lightrag_search import lightrag_search
from graphrag_kb_server.model.chat_response import ChatResponse
from graphrag_kb_server.model.search.search import (
    SummarisationRequestWithDocumentPath,
    SummarisationRequest,
    SummarisationResponse,
    SearchResults,
)
from graphrag_kb_server.service.google_ai_client import structured_completion

DOCUMENT_PATHS_LIMIT = 10


async def retrieve_relevant_documents(
    project_dir: Path, query: DocumentSearchQuery
) -> SearchResults:
    """
    Searches documents that are relevant to the query and summarizes them according to the user's profile and question.

    Args:
        project_dir: The directory of the project
        query: The query to search for documents

    Returns:
        A list of summarization responses with document paths
    """
    chat_response = await search_documents(project_dir, query)
    document_paths = []
    for reference in chat_response.response["references"][:DOCUMENT_PATHS_LIMIT]:
        docs = reference["file"].split("<SEP>")
        document_paths.append(docs[0])
    promises = []
    for document_path in document_paths:
        summarisation_request = SummarisationRequestWithDocumentPath(
            user_profile=query.user_profile,
            question=query.question,
            document_path=document_path,
        )
        promises.append(
            summarize_document_with_document_path(project_dir, summarisation_request)
        )
    summaries_with_document_paths = []
    summaries: list[SummarisationResponse] = await asyncio.gather(*promises)
    # Summarize and score
    for i in range(len(document_paths)):
        summaries_with_document_paths.append(
            SummarisationResponseWithDocument(
                summary=summaries[i].summary,
                relevancy_score=summaries[i].relevancy_score,
                relevance=summaries[i].relevance,
                document_path=document_paths[i],
            )
        )
    summaries_with_document_paths = sorted(
        summaries_with_document_paths,
        key=lambda x: x.get_relevancy_score_points(),
        reverse=True,
    )
    response = chat_response.response["response"]
    return SearchResults(
        documents=summaries_with_document_paths,
        response=response,
    )


async def search_documents(
    project_dir: Path, query: DocumentSearchQuery
) -> ChatResponse:
    question = generate_question(query)
    query_params = generate_query(project_dir, query, question)
    return await lightrag_search(query_params)


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
    summarisation_response_dict = await structured_completion(
        prompts["document-summarization"]["system_prompt"],
        user_prompt,
        SummarisationResponse,
    )
    return SummarisationResponse(**summarisation_response_dict)


def generate_query(
    project_dir: Path, query: DocumentSearchQuery, question: str
) -> QueryParameters:
    query_params = QueryParameters(
        format="json",
        search="hybrid",
        engine=Engine.LIGHTRAG,
        context_params=ContextParameters(
            query=question,
            project_dir=project_dir,
            context_size=8000,
        ),
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
    )
    return query_params


def generate_question(document_search_query: DocumentSearchQuery) -> str:
    template = prompts["document-retrieval"]["question-template"]

    def format_keywords(match_output: MatchOutput, high_level: bool) -> str:
        res = ""
        for classification in match_output.entity_dict.values():
            for entity in classification.entities:
                if high_level and entity.abstraction == Abstraction.HIGH_LEVEL:
                    res += f"- {entity.entity}\n  {entity.reasoning}\n"
                else:
                    res += f"- {entity.entity}\n  {entity.reasoning}\n"
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

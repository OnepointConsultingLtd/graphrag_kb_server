

from graphrag_kb_server.model.search.match_query import MatchOutput
from graphrag_kb_server.model.search.search import DocumentSearchQuery, RelevanceScore, SearchResults, SummarisationResponseWithDocument


def create_search_history() -> DocumentSearchQuery:
    return DocumentSearchQuery(
        request_id="test_request_id",
        linkedin_profile_url="test_linkedin_profile_url",
        organisation_role="test_organisation_role",
        organisation_type="test_organisation_type",
        business_type="test_business_type",
        question="test_question",
        user_profile="test_user_profile",
        topics_of_interest=MatchOutput(entity_dict={}),
        max_filepath_depth=1000,
        is_search_query=True,
        biggest_challenge="test_biggest_challenge",
    )

def create_search_results(search_query: DocumentSearchQuery) -> SearchResults:
    return SearchResults(
        request_id=search_query.request_id,
        documents=[
            SummarisationResponseWithDocument(
                summary="test_summary",
                relevance="test_relevance",
                relevancy_score=RelevanceScore.HIGH,
                document_path="test_document_path",
                main_keyword="test_main_keyword",
            )
        ],
    )
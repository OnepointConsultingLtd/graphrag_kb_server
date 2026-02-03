from graphrag_kb_server.model.search.keywords import KeywordType, Keywords
from graphrag_kb_server.model.search.search import (
    DocumentSearchQuery,
    SearchResults,
    SummarisationResponseWithDocument,
    RelevanceScore,
)
from graphrag_kb_server.model.search.match_query import MatchOutput
from graphrag_kb_server.model.search.entity import EntityWithScore, Abstraction
from graphrag_kb_server.model.search.entity import EntityList


COMMON_REQUEST_ID = "1234567890"


def create_document_search_query() -> DocumentSearchQuery:
    return DocumentSearchQuery(
        generated_user_id="1234567890",
        question="How can I use AI to improve my automation and achieve truly autonomous systems?",
        user_profile="I am a software engineer with a passion for building scalable and efficient systems.",
        biggest_challenge="I want to improve my automation and achieve truly autonomous systems.",
        linkedin_profile_url="https://www.linkedin.com/in/john-doe-1234567890/",
        organisation_role="CEO",
        organisation_type="SME",
        business_type="Consultancy",
        request_id=COMMON_REQUEST_ID,
        topics_of_interest=MatchOutput(
            entity_dict={
                "category": EntityList(
                    entities=[
                        EntityWithScore(
                            entity="AI",
                            score=0.9,
                            reasoning="The user is interested in AI",
                            abstraction=Abstraction.HIGH_LEVEL,
                        )
                    ]
                ),
            }
        ),
    )


def create_search_results() -> SearchResults:
    return SearchResults(
        response="The user is interested in AI",
        request_id=COMMON_REQUEST_ID,
        documents=[
            SummarisationResponseWithDocument(
                summary="The user is interested in AI",
                relevance="The user is interested in AI",
                relevancy_score=RelevanceScore.HIGH,
                document_path="/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/input/clustre/Case studies/Case_Study_-_AIMIA_and_Zuhlke.txt",
                main_keyword="AIMIA and Zuhlke",
            )
        ],
    )


def create_keywords_high_level(search_history_id: int) -> Keywords:
    return Keywords(
        keywords=["AI", "Automation", "Autonomous Systems"],
        keyword_type=KeywordType.HIGH_LEVEL,
        search_id=search_history_id,
    )


def create_keywords_low_level(search_history_id: int) -> Keywords:
    return Keywords(
        keywords=["Be Informed", "Zuehlke"],
        keyword_type=KeywordType.LOW_LEVEL,
        search_id=search_history_id,
    )

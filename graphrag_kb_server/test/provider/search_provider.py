from graphrag_kb_server.model.search.search import DocumentSearchQuery
from graphrag_kb_server.model.search.match_query import MatchOutput
from graphrag_kb_server.model.search.entity import EntityWithScore, Abstraction
from graphrag_kb_server.model.search.entity import EntityList


def create_document_search_query() -> DocumentSearchQuery:
    return DocumentSearchQuery(
        question="How can I use AI to improve my automation and achieve truly autonomous systems?",
        user_profile="I am a software engineer with a passion for building scalable and efficient systems.",
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

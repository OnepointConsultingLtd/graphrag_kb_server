
from graphrag_kb_server.model.search.entity import Entity
from graphrag_kb_server.model.search.match_query import MatchQuery, MatchOutput

def create_match_query() -> MatchQuery:
    topics_of_interest = [
        Entity(
            name="Artificial Intelligence (AI)",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Technology",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Java",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="AI",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Business",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Applications",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Digital Transformation",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Cloud",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Compliance",
            type="category",
            description="Process automation and workflow optimization",
        ),
    ]
    return MatchQuery(
        question="How can I use AI to improve my automation and achieve truly autonomous systems?",
        user_profile="I am a software engineer interested in automation and Robotics",
        topics_of_interest=tuple(topics_of_interest),
        entity_types=tuple(["category"]),
        entities_limit=30,
    )

def create_match_output() -> MatchOutput:
    return MatchOutput(
        entities=[
            Entity(
                name="AI",
                type="category",
                description="Artificial Intelligence and Machine Learning",
            ),
        ]
    )
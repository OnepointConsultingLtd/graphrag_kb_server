import asyncio
from graphrag_kb_server.model.topics import (
    SimilarityTopics,
    SimilarityTopic,
)
from graphrag_kb_server.service.topics_post_processing import post_process_topics


def test_post_process_topics():
    topics = SimilarityTopics(
        topics=[
            SimilarityTopic(
                name="AI",
                type="category",
                description="AI is a technology that allows machines to learn and make decisions based on data.",
                probability=0.9,
            ),
            SimilarityTopic(
                name="Artificial Intelligence",
                type="category",
                description="Artificial Intelligence is a technology that allows machines to learn and make decisions based on data.",
                probability=0.8,
            ),
            SimilarityTopic(
                name="Machine Learning",
                type="category",
                description="Machine Learning is a technology that allows machines to learn and make decisions based on data.",
                probability=0.7,
            ),
        ]
    )
    topics_prompt = "Please ensure that you deduplicate the topics and remove the duplicates. If a topic is a synonym of another topic, choose the one with the most thourgh description."
    topics = asyncio.run(post_process_topics(topics, topics_prompt))
    assert len(topics.topics) == 2


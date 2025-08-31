from graphrag_kb_server.model.topics import (
    SimilarityTopics,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.google_ai_client import structured_completion


def shorten(topics: SimilarityTopics):
    limit = 1024
    for t in topics.topics:
        has_more = len(t.description) > limit
        t.description = t.description[:limit]
        if has_more:
            t.description += "..."


async def post_process_topics(topics: SimilarityTopics, topics_prompt: str) -> SimilarityTopics:
    shorten(topics)
    topics_str = "\n\n".join([topic.markdown() for topic in topics.topics])
    prompt_path = "topics-post-processing"
    user_prompt = prompts[prompt_path]["user_prompt"].format(
        topics=topics_str, topics_prompt=topics_prompt
    )
    system_prompt = prompts[prompt_path]["system_prompt"]
    topics_dict = await structured_completion(
        system_prompt, user_prompt, SimilarityTopics
    )
    return SimilarityTopics(**topics_dict)
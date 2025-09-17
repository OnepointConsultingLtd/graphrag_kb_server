from graphrag_kb_server.model.topics import (
    SimilarityTopics,
    Topics,
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


async def _execute_prompt(
    prompt_path: str,
    topics: SimilarityTopics | Topics,
    topics_prompt: str | None = None,
) -> SimilarityTopics:
    shorten(topics)
    topics_str = "\n\n".join([topic.markdown() for topic in topics.topics])
    format_params = {
        "topics": topics_str,
    }
    if topics_prompt:
        format_params["topics_prompt"] = topics_prompt
    user_prompt = prompts[prompt_path]["user_prompt"].format(**format_params)
    system_prompt = prompts[prompt_path]["system_prompt"]
    topics_dict = await structured_completion(
        system_prompt, user_prompt, SimilarityTopics
    )
    return SimilarityTopics(**topics_dict)


async def post_process_topics(
    topics: SimilarityTopics | Topics, topics_prompt: str
) -> SimilarityTopics:
    prompt_path = "topics-post-processing"
    return await _execute_prompt(prompt_path, topics, topics_prompt)


async def deduplicate_topics(topics: SimilarityTopics | Topics) -> SimilarityTopics:
    prompt_path = "topics-deduplication"
    return await _execute_prompt(prompt_path, topics)

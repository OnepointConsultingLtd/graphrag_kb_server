from pathlib import Path

from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import Topics, TopicQuestions, TopicsRequest
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.topic_generation import generate_topics
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.utils.cache import GenericSimpleCache


question_generation_cache = GenericSimpleCache[str, TopicQuestions]()


async def generate_questions_from_topics(
    project_dir: Path, engine: Engine, limit: int, entity_type_filter: str
) -> TopicQuestions:
    cache_key = f"{project_dir.as_posix()}_{engine.value}_{limit}_{entity_type_filter}"
    cached_questions = question_generation_cache.get(cache_key)
    if cached_questions is not None:
        return cached_questions
    topics = await generate_topics(
        TopicsRequest(
            project_dir=project_dir,
            engine=engine,
            limit=limit,
            add_questions=False,
            entity_type_filter=entity_type_filter,
        )
    )
    question_generation_cache.set(cache_key, await generate_questions(topics))
    return await generate_questions(topics)


async def generate_questions(topics: Topics) -> TopicQuestions:
    topics_str = "\n\n".join([topic.markdown() for topic in topics.topics])
    user_prompt = prompts["question-generation"]["user_prompt"].format(
        topics=topics_str
    )
    topic_questions_dict = await structured_completion(
        prompts["question-generation"]["system_prompt"], user_prompt, TopicQuestions
    )
    return TopicQuestions(**topic_questions_dict)

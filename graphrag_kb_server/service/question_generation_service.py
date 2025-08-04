from pathlib import Path

from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import Topics, TopicQuestions, TopicsRequest, QuestionsQuery
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.topic_generation import generate_topics
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.utils.cache import GenericSimpleCache


question_generation_cache = GenericSimpleCache[str, TopicQuestions]()


async def generate_questions_from_topics(
    questions_query: QuestionsQuery
) -> TopicQuestions:
    project_dir: Path = questions_query.project_dir
    engine: Engine = questions_query.engine
    limit: int = questions_query.limit
    entity_type_filter: str = questions_query.entity_type_filter
    topics_str: str = questions_query.topics_str
    cache_key = f"{project_dir.as_posix()}_{engine.value}_{limit}_{entity_type_filter}_{topics_str}"
    cached_questions = question_generation_cache.get(cache_key)
    if cached_questions is not None:
        return cached_questions
    if topics_str and len(topics_str) > 0:
        topics = topics_str.split(";")
    else:
        topics = []
    topics = await generate_topics(
        TopicsRequest(
            project_dir=project_dir,
            engine=engine,
            limit=limit,
            add_questions=False,
            entity_type_filter=entity_type_filter,
            topics=topics,
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

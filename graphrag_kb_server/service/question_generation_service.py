from pathlib import Path

from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import (
    Topics,
    TopicQuestions,
    TopicsRequest,
    QuestionsQuery,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.topic_generation import generate_topics
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.utils.cache import GenericSimpleCache
from graphrag_kb_server.service.lightrag.lightrag_related_topics import (
    get_keywords_from_text,
)
from graphrag_kb_server.service.graphrag.query import rag_local_entities
from graphrag_kb_server.model.rag_parameters import ContextParameters

question_generation_cache = GenericSimpleCache[str, TopicQuestions]()


async def generate_questions_from_topics(
    questions_query: QuestionsQuery,
) -> TopicQuestions:
    project_dir: Path = questions_query.project_dir
    engine: Engine = questions_query.engine
    limit: int = questions_query.limit
    entity_type_filter: str = questions_query.entity_type_filter
    topics: list[str] = questions_query.topics
    cache_key = f"{project_dir.as_posix()}_{engine.value}_{limit}_{entity_type_filter}_{";".join(topics)}"
    cached_questions = question_generation_cache.get(cache_key)
    if cached_questions is not None:
        return cached_questions
    if (
        len(topics) == 0
        and questions_query.text
        and len(questions_query.text.strip()) > 0
    ):
        match engine:
            case Engine.LIGHTRAG:
                topics = await get_keywords_from_text(
                    questions_query.text, project_dir, None
                )
            case Engine.GRAPHRAG:
                topics = rag_local_entities(
                    ContextParameters(
                        query=questions_query.text, project_dir=project_dir
                    )
                )
                topics = [t["entity"] for t in topics[:limit]]
            case _:
                raise ValueError(
                    f"Engine {engine} not supported for text-based question generation"
                )

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

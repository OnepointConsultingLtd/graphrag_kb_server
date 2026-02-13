from pathlib import Path

from graphrag_kb_server.service.db.db_persistence_topics import (
    find_questions,
    save_questions,
)
from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import (
    Topics,
    Topic,
    TopicQuestions,
    QuestionsQuery,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.lightrag.lightrag_related_topics import (
    get_keywords_from_text,
)
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
)


async def generate_questions_from_topics(
    questions_query: QuestionsQuery,
) -> TopicQuestions:
    project_dir: Path = questions_query.project_dir
    engine: Engine = questions_query.engine
    limit: int = questions_query.limit
    topics: list[str] = questions_query.topics
    cached_questions = await find_questions(questions_query)
    if cached_questions is not None and len(cached_questions.topic_questions) > 0:
        return cached_questions
    topics = [t for t in topics if t and len(t.strip()) > 0]
    misses_topics = len(topics) == 0
    has_text = questions_query.text and len(questions_query.text.strip()) > 0
    if misses_topics and not has_text:
        raise ValueError("No topics or text provided")
    if misses_topics and has_text:
        match engine:
            case Engine.LIGHTRAG:
                topics = await get_keywords_from_text(
                    questions_query.text, project_dir, None
                )
            case _:
                raise ValueError(
                    f"Engine {engine} not supported for text-based question generation"
                )
    else:
        match engine:
            case _:
                nodes = create_network_from_project_dir(project_dir).nodes
                topics = [nodes[t]["entity_id"] for t in topics if t in nodes]

    match engine:
        case Engine.LIGHTRAG:
            nodes = create_network_from_project_dir(project_dir).nodes
            topics = [
                Topic(
                    name=nodes[t]["entity_id"],
                    description=nodes[t]["description"],
                    type=nodes[t]["entity_type"],
                )
                for t in topics
            ]

    generated_questions = await generate_questions(
        Topics(topics=topics), questions_query.system_prompt
    )

    await save_questions(questions_query, generated_questions)
    return generated_questions


async def generate_questions(topics: Topics, system_prompt: str) -> TopicQuestions:
    topics_str = "\n\n".join([topic.markdown() for topic in topics.topics])
    user_prompt = prompts["question-generation"]["user_prompt"].format(
        topics=topics_str
    )
    system_prompt = system_prompt or prompts["question-generation"]["system_prompt"]
    topic_questions_dict = await structured_completion(
        system_prompt, user_prompt, TopicQuestions
    )
    return TopicQuestions(**topic_questions_dict)

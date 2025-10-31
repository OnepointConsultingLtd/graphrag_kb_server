from pathlib import Path

from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import (
    Topics,
    Topic,
    TopicQuestions,
    QuestionsQuery,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.utils.cache import GenericSimpleCache
from graphrag_kb_server.service.lightrag.lightrag_related_topics import (
    get_keywords_from_text,
)
from graphrag_kb_server.service.graphrag.query import rag_local_entities
from graphrag_kb_server.model.rag_parameters import ContextParameters
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
)
from graphrag_kb_server.service.graphrag.graph_support import read_graphrag_project

question_generation_cache = GenericSimpleCache[str, TopicQuestions]()


async def generate_questions_from_topics(
    questions_query: QuestionsQuery,
) -> TopicQuestions:
    project_dir: Path = questions_query.project_dir
    engine: Engine = questions_query.engine
    limit: int = questions_query.limit
    entity_type_filter: str = questions_query.entity_type_filter
    topics: list[str] = questions_query.topics
    cache_key = f"{project_dir.as_posix()}_{engine.value}_{limit}_{entity_type_filter}_{";".join(topics)}_{questions_query.text}_{questions_query.system_prompt}"
    cached_questions = question_generation_cache.get(cache_key)
    if cached_questions is not None:
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
    else:
        match engine:
            case Engine.GRAPHRAG:   
                nodes = read_graphrag_project(project_dir).nodes
                topics = [nodes[t.upper()]["name"] for t in topics if t.upper() in nodes]
            case Engine.LIGHTRAG:
                nodes = create_network_from_project_dir(project_dir).nodes
                topics = [nodes[t]["entity_id"] for t in topics if t in nodes]

    match engine:
        case Engine.GRAPHRAG:
            nodes = read_graphrag_project(project_dir).nodes
            topics = [Topic(name=nodes[t]["name"], description=nodes[t]["description"], type=nodes[t]["type"]) for t in topics]
        case Engine.LIGHTRAG:
            nodes = create_network_from_project_dir(project_dir).nodes
            topics = [Topic(name=nodes[t]["entity_id"], description=nodes[t]["description"], type=nodes[t]["entity_type"]) for t in topics]
        
    question_generation_cache.set(
        cache_key,
        generated_questions := await generate_questions(
            Topics(topics=topics), questions_query.system_prompt
        ),
    )
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

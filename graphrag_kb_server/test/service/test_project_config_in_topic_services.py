"""The question generation and topic services use the configuration of the project they run for."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import (
    QuestionsQuery,
    SimilarityTopics,
    Topic,
    Topics,
    TopicsRequest,
    TopicQuestions,
)
from graphrag_kb_server.service import (
    question_generation_service,
    topic_generation,
    topics_post_processing,
)
from graphrag_kb_server.service.project_config_service import ProjectConfig

PROJECT_DIR = Path("/root/tenant/lightrag/project")
CONFIG = replace(
    ProjectConfig.from_env(), gemini_api_key="project-key", project_label="tenant/project"
)

SIMILARITY_ANSWER = {
    "topics": [
        {"name": "AI", "type": "category", "description": "d", "probability": 0.9}
    ]
}


@pytest.fixture
def sample_topics() -> Topics:
    return Topics(topics=[Topic(name="AI", description="d", type="category")])


@pytest.mark.asyncio
async def test_generate_questions_forwards_the_config(monkeypatch, sample_topics):
    completion = AsyncMock(return_value={"topic_questions": []})
    monkeypatch.setattr(question_generation_service, "structured_completion", completion)
    await question_generation_service.generate_questions(sample_topics, "sys", CONFIG)
    assert completion.call_args.kwargs["config"] is CONFIG


@pytest.mark.asyncio
async def test_generate_questions_from_topics_resolves_config_of_the_project(monkeypatch):
    nodes = {"T1": {"entity_id": "T1", "description": "d", "entity_type": "category"}}
    config_lookup = AsyncMock(return_value=CONFIG)
    generate = AsyncMock(return_value=TopicQuestions(topic_questions=[]))
    monkeypatch.setattr(question_generation_service, "find_questions", AsyncMock(return_value=None))
    monkeypatch.setattr(question_generation_service, "save_questions", AsyncMock())
    monkeypatch.setattr(
        question_generation_service,
        "create_network_from_project_dir",
        lambda project_dir: SimpleNamespace(nodes=nodes),
    )
    monkeypatch.setattr(question_generation_service, "get_project_config_for_dir", config_lookup)
    monkeypatch.setattr(question_generation_service, "generate_questions", generate)

    await question_generation_service.generate_questions_from_topics(
        QuestionsQuery(
            project_dir=PROJECT_DIR,
            engine=Engine.LIGHTRAG,
            limit=1,
            entity_type_filter="",
            topics=["T1"],
        )
    )

    config_lookup.assert_awaited_once_with(PROJECT_DIR)
    assert generate.call_args.args[2] is CONFIG


@pytest.mark.asyncio
async def test_post_process_topics_forwards_the_config(monkeypatch, sample_topics):
    completion = AsyncMock(return_value=SIMILARITY_ANSWER)
    monkeypatch.setattr(topics_post_processing, "structured_completion", completion)
    await topics_post_processing.post_process_topics(sample_topics, "be brief", CONFIG)
    assert completion.call_args.kwargs["config"] is CONFIG


@pytest.mark.asyncio
async def test_deduplicate_topics_forwards_the_config(monkeypatch, sample_topics):
    completion = AsyncMock(return_value=SIMILARITY_ANSWER)
    monkeypatch.setattr(topics_post_processing, "structured_completion", completion)
    result = await topics_post_processing.deduplicate_topics(sample_topics, CONFIG)
    assert isinstance(result, SimilarityTopics)
    assert completion.call_args.kwargs["config"] is CONFIG


@pytest.mark.asyncio
async def test_generate_topics_deduplicates_with_the_config_of_the_project(monkeypatch):
    generated = Topics(topics=[Topic(name="AI", description="d", type="category")])
    deduplicate = AsyncMock(return_value="deduplicated")
    config_lookup = AsyncMock(return_value=CONFIG)
    monkeypatch.setattr(
        topic_generation,
        "find_topics_by_project_name",
        AsyncMock(side_effect=[None, generated]),
    )
    monkeypatch.setattr(topic_generation, "_generate_topics_lightrag", AsyncMock(return_value=generated))
    monkeypatch.setattr(topic_generation, "save_topics_request", AsyncMock())
    monkeypatch.setattr(topic_generation, "deduplicate_topics", deduplicate)
    monkeypatch.setattr(topic_generation, "get_project_config_for_dir", config_lookup)

    result = await topic_generation.generate_topics(
        TopicsRequest(
            project_dir=PROJECT_DIR, engine=Engine.LIGHTRAG, deduplicate_topics=True
        )
    )

    assert result == "deduplicated"
    config_lookup.assert_awaited_once_with(PROJECT_DIR)
    deduplicate.assert_awaited_once_with(generated, CONFIG)


@pytest.mark.asyncio
async def test_generate_topics_without_deduplication_does_not_resolve_config(monkeypatch):
    generated = Topics(topics=[Topic(name="AI", description="d", type="category")])
    config_lookup = AsyncMock(return_value=CONFIG)
    monkeypatch.setattr(
        topic_generation,
        "find_topics_by_project_name",
        AsyncMock(side_effect=[None, generated]),
    )
    monkeypatch.setattr(topic_generation, "_generate_topics_lightrag", AsyncMock(return_value=generated))
    monkeypatch.setattr(topic_generation, "save_topics_request", AsyncMock())
    monkeypatch.setattr(topic_generation, "get_project_config_for_dir", config_lookup)

    await topic_generation.generate_topics(
        TopicsRequest(project_dir=PROJECT_DIR, engine=Engine.LIGHTRAG)
    )

    config_lookup.assert_not_awaited()

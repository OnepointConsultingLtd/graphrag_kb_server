import pytest

from graphrag_kb_server.service.db.db_persistence_topics import (
    create_topics_table,
    drop_topics_table,
    insert_topic,
    find_topics_by_project_name,
    save_topics_request,
    delete_topics_by_project_name,
)
from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topic, TopicsRequest
from graphrag_kb_server.test.service.db.common_test_support import (
    create_test_project_wrapper,
    create_project_dir,
)


@pytest.mark.asyncio
async def test_create_topic():

    async def test_function(
        full_project: FullProject,
        found_project: Project,
        schema_name: str,
        project_name: str,
    ):
        # Create topics table and insert topic
        try:
            await create_topics_table(schema_name)
            topic = Topic(
                name=f"{project_name}_topic",
                description="test_description",
                type="test_type",
                questions=[],
                project_id=found_project.id,
            )
            topic_id = await insert_topic(schema_name, topic)
            assert topic_id is not None
            assert topic_id != 0
            project_dir = create_project_dir(
                schema_name, full_project.engine, project_name
            )
            topics_request = TopicsRequest(
                engine=full_project.engine,
                project_dir=project_dir,
                topics=[],
                add_questions=False,
                entity_type_filter="",
                deduplicate_topics=False,
                limit=20,
            )
            topics = await find_topics_by_project_name(topics_request)
            assert len(topics.topics) == 1
            assert topics.topics[0].id == topic_id
            assert topics.topics[0].name == topic.name
            assert topics.topics[0].description == topic.description
            assert topics.topics[0].type == topic.type
            assert topics.topics[0].questions == topic.questions
            assert topics.topics[0].project_id == found_project.id
            topics_request = TopicsRequest(
                engine=Engine.GRAPHRAG,
                project_dir=project_dir,
                topics=[],
                add_questions=False,
                entity_type_filter="category",
                deduplicate_topics=False,
                limit=20,
            )
            await delete_topics_by_project_name(
                schema_name, project_name, full_project.engine
            )
            await save_topics_request(topics_request, topics)
        finally:
            await drop_topics_table(schema_name)

    await create_test_project_wrapper(test_function)

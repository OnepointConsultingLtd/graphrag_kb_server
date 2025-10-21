import pytest

from datetime import datetime

from graphrag_kb_server.service.db.db_persistence_topics import (
    create_topics_table,
    drop_topics_table,
    insert_topic,
    find_topics_by_project_name,
    save_topics_request,
    delete_topics_by_project_name
)
from graphrag_kb_server.service.db.db_persistence_project import (
    create_project,
    delete_project,
    create_project_table,
    drop_project_table,
    find_project_by_name,
)
from graphrag_kb_server.model.project import FullProject, Project
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topic, TopicsRequest, Topics
from graphrag_kb_server.config import cfg


@pytest.mark.asyncio
async def test_create_topic():
    schema_name = "public"
    project_name = "test_project"
    full_project = FullProject(
        schema_name=schema_name,
        engine=Engine.GRAPHRAG,
        project=Project(
            name=project_name,
            updated_timestamp=datetime.now(),
            input_files=[],
            indexing_status=IndexingStatus.NOT_STARTED,
        ),
    )
    try:
        # Create project table, project, and topics table
        await create_project_table(schema_name)
        await create_project(full_project)

        found_project = await find_project_by_name(
            schema_name, full_project.project.name
        )
        assert found_project is not None
        assert found_project.id != full_project.id
        
        # Create topics table and insert topic
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
        topics = await find_topics_by_project_name(schema_name, project_name, full_project.engine)
        assert len(topics) == 1
        assert topics[0].id == topic_id
        assert topics[0].name == topic.name
        assert topics[0].description == topic.description
        assert topics[0].type == topic.type
        assert topics[0].questions == topic.questions
        assert topics[0].project_id == found_project.id
        topics_request = TopicsRequest(
            engine=Engine.GRAPHRAG,
            project_dir=cfg.graphrag_root_dir_path / schema_name / project_name,
            topics=[],
            add_questions=False,
            entity_type_filter="category",
            deduplicate_topics=False,
            limit=20,
        )
        await delete_topics_by_project_name(schema_name, project_name, full_project.engine)
        await save_topics_request(topics_request, Topics(topics=topics))

    finally:
        await drop_topics_table(schema_name)
        await delete_project(full_project)
        await drop_project_table(full_project)

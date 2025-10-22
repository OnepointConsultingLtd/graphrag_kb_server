from graphrag_kb_server.model.topics import Topic
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    execute_query_with_return,
    fetch_all,
)
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS
from graphrag_kb_server.model.topics import TopicsRequest, Topics
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.db.common_operations import clear_table, get_project_id

TB_TOPICS = "TB_TOPICS"


async def create_topics_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_TOPICS} (
	ID SERIAL NOT NULL,
	NAME TEXT NOT NULL,
    DESCRIPTION TEXT NOT NULL,
    TYPE TEXT NOT NULL,
    QUESTIONS TEXT[] DEFAULT '{{}}',
    PROJECT_ID INTEGER NOT NULL,
    ACTIVE BOOLEAN NOT NULL DEFAULT TRUE,
    CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (ID),
	UNIQUE (NAME, PROJECT_ID),
    CONSTRAINT PROJECT_ID
		FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID) 
		MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_topics_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_TOPICS};
"""
    )


async def insert_topic(schema_name: str, topic: Topic) -> int:
    res = await execute_query_with_return(
        f"""
INSERT INTO {schema_name}.{TB_TOPICS} (NAME, DESCRIPTION, TYPE, QUESTIONS, PROJECT_ID) VALUES ($1, $2, $3, $4, $5)
RETURNING ID;
""",
        topic.name,
        topic.description,
        topic.type,
        topic.questions,
        topic.project_id,
    )
    return res


async def delete_topics_by_project_name(
    schema_name: str, project_name: str, engine: Engine
):
    await clear_table(schema_name, project_name, engine, TB_TOPICS)


async def find_topics_by_project_name(topics_request: TopicsRequest) -> Topics:
    schema_name = topics_request.project_dir.parent.parent.name
    project_name = topics_request.project_dir.name
    engine = topics_request.engine
    limit = topics_request.limit
    entity_type_filter = topics_request.entity_type_filter
    type_filter = ""
    if entity_type_filter != "":
        type_filter = f" AND TYPE = '{entity_type_filter}' "
    result = await fetch_all(
        f"""
SELECT * FROM {schema_name}.{TB_TOPICS} WHERE PROJECT_ID = 
(SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $1 AND ENGINE = $2) 
AND ACTIVE = TRUE {type_filter} ORDER BY ID ASC LIMIT $3;
""",
        project_name,
        engine.value,
        limit,
    )
    topics = [
        Topic(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"],
            type=row["type"],
            questions=row["questions"],
            project_id=int(row["project_id"]),
        )
        for row in result
    ]
    return Topics(topics=topics)


async def save_topics_request(topics_request: TopicsRequest, topics: Topics) -> int:
    engine = topics_request.engine.value
    project_dir = topics_request.project_dir
    project_name = project_dir.name
    schema_name = project_dir.parent.parent.name
    project_id = await get_project_id(schema_name, project_name, engine)
    for topic in topics.topics:
        topic_with_id = topic.model_copy(update={"id": None, "project_id": project_id})
        await insert_topic(schema_name, topic_with_id)

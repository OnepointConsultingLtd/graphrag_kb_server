from pathlib import Path
from typing import Final, Generator
import pandas as pd

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topics, Topic, TopicsRequest
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
)
from graphrag_kb_server.service.cag.cag_support import extract_main_topics
from graphrag_kb_server.service.topics_post_processing import deduplicate_topics
from graphrag_kb_server.service.db.db_persistence_topics import (
    save_topics_request,
    find_topics_by_project_name,
)


async def generate_topics(topics_request: TopicsRequest) -> Topics:
    result = await find_topics_by_project_name(topics_request)
    if result is not None and len(result.topics) > 0:
        return result
    match topics_request.engine:
        case Engine.LIGHTRAG:
            result = await _generate_topics_lightrag(topics_request)
        case Engine.CAG:
            result = await _generate_topics_cag(topics_request)
    await save_topics_request(topics_request, result)
    result = await find_topics_by_project_name(topics_request)
    if topics_request.deduplicate_topics and result is not None:
        result = await deduplicate_topics(result)
    return result


def convert_topics_to_pandas(topics: Topics) -> pd.DataFrame:
    df = pd.DataFrame([topic.model_dump() for topic in topics.topics])
    df.columns = ["id", "name", "description", "type", "questions", "project_id"]
    return df


def _generate_rows(df: pd.DataFrame, limit: int) -> Generator[pd.Series, None, None]:
    for _, row in df[:limit].iterrows():
        yield row


TOP_LEVEL: Final[int] = 0


def _generate_topics_graphrag(topics_request: TopicsRequest) -> Topics:
    df = get_entity_centrality_as_pd(topics_request.project_dir)
    if topics_request.topics and len(topics_request.topics) > 0:
        df = df[df["entity_id"].isin(topics_request.topics)]
    topics = [
        Topic(
            name=row["entity_id"],
            description=row["description"],
            type=row["entity_type"],
            questions=[],
        )
        for row in _generate_rows(df, topics_request.limit)
    ]
    return Topics(topics=topics)


async def _generate_topics_lightrag(topics_request: TopicsRequest) -> Topics:
    centrality_scores = await get_sorted_centrality_scores_as_pd(
        topics_request.project_dir
    )
    if topics_request.topics and len(topics_request.topics) > 0:
        centrality_scores = centrality_scores[
            centrality_scores["entity_id"].isin(topics_request.topics)
        ]
    limit = 100000  # limit of the request is applied now when accessing the database.
    topics = [
        Topic(
            name=row["entity_id"],
            description=row["description"],
            type=row["entity_type"],
            questions=[],
        )
        for row in _generate_rows(centrality_scores, limit)
    ]
    return Topics(topics=topics)


async def _generate_topics_cag(topics_request: TopicsRequest) -> Topics:
    limit = topics_request.limit
    topics = await extract_main_topics(topics_request.project_dir)
    return Topics(topics=topics.topics[:limit])


if __name__ == "__main__":

    import asyncio

    def test_lightrag():
        project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
        topics = asyncio.run(
            generate_topics(
                TopicsRequest(project_dir=project_dir, engine=Engine.LIGHTRAG)
            )
        )
        return topics

    topics = test_lightrag()
    df = convert_topics_to_pandas(topics)
    print(df)

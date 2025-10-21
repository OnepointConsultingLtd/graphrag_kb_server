from pathlib import Path
from typing import Final, Generator
import pandas as pd

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topics, Topic, TopicsRequest
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
)
from graphrag_kb_server.service.graphrag.entity_centrality import (
    get_entity_centrality_as_pd,
)
from graphrag_kb_server.service.cag.cag_support import extract_main_topics
from graphrag_kb_server.service.topics_post_processing import deduplicate_topics
from graphrag_kb_server.utils.cache import GenericSimpleCache


topics_cache = GenericSimpleCache[Topics, TopicsRequest]()


async def generate_topics(topics_request: TopicsRequest) -> Topics:
    result = topics_cache.get(topics_request)
    if result is not None:
        return result
    match topics_request.engine:
        case Engine.GRAPHRAG:
            result = _generate_topics_graphrag(topics_request)
        case Engine.LIGHTRAG:
            result = _generate_topics_lightrag(topics_request)
        case Engine.CAG:
            result = await _generate_topics_cag(topics_request)
    if topics_request.deduplicate_topics and result is not None:
        result = await deduplicate_topics(result)
    topics_cache.set(topics_request, result)
    return result


def convert_topics_to_pandas(topics: Topics) -> pd.DataFrame:
    df = pd.DataFrame([topic.model_dump() for topic in topics.topics])
    df.columns = ["name", "description", "type", "questions"]
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


def _generate_topics_lightrag(topics_request: TopicsRequest) -> Topics:
    centrality_scores = get_sorted_centrality_scores_as_pd(topics_request.project_dir)
    if topics_request.entity_type_filter != "":
        centrality_scores = centrality_scores[
            centrality_scores["entity_type"] == topics_request.entity_type_filter
        ]
    if topics_request.topics and len(topics_request.topics) > 0:
        centrality_scores = centrality_scores[
            centrality_scores["entity_id"].isin(topics_request.topics)
        ]
    topics = [
        Topic(
            name=row["entity_id"],
            description=row["description"],
            type=row["entity_type"],
            questions=[],
        )
        for row in _generate_rows(centrality_scores, topics_request.limit)
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

    def test_graphrag():
        project_dir = Path("/var/graphrag/tennants\gil_fernandes/graphrag/dwell")
        topics = asyncio.run(
            generate_topics(
                TopicsRequest(project_dir=project_dir, engine=Engine.GRAPHRAG)
            )
        )
        return topics

    topics = test_graphrag()
    df = convert_topics_to_pandas(topics)
    print(df)

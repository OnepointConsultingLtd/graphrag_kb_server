from pathlib import Path
from typing import Final, Generator
import pandas as pd

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topics, Topic, TopicsRequest
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
)
from graphrag_kb_server.service.community_service import prepare_community_extraction


def generate_topics(topics_request: TopicsRequest) -> Topics:
    match topics_request.engine:
        case Engine.GRAPHRAG:
            return _generate_topics_graphrag(topics_request)
        case Engine.LIGHTRAG:
            return _generate_topics_lightrag(topics_request)
        case _:
            raise ValueError(f"Engine {topics_request.engine} not supported")


def _generate_rows(df: pd.DataFrame, limit: int) -> Generator[pd.Series, None, None]:
    for _, row in df[:limit].iterrows():
        yield row


TOP_LEVEL: Final[int] = 0


def _generate_topics_graphrag(topics_request: TopicsRequest) -> Topics:
    df = prepare_community_extraction(topics_request.project_dir, [TOP_LEVEL])
    topics = [
        Topic(
            name=row["title_y"],
            description=row["summary"],
            type=row["title_y"],
            questions=[],
        )
        for row in _generate_rows(df, topics_request.limit)
    ]
    return Topics(topics=topics)


def _generate_topics_lightrag(topics_request: TopicsRequest) -> Topics:
    centrality_scores = get_sorted_centrality_scores_as_pd(topics_request.project_dir)
    if topics_request.entity_type_filter != "":
        centrality_scores = centrality_scores[centrality_scores["entity_type"] == topics_request.entity_type_filter]
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


if __name__ == "__main__":

    def test_lightrag():
        project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
        topics = generate_topics(
            TopicsRequest(project_dir=project_dir, engine=Engine.LIGHTRAG)
        )
        return topics

    def test_graphrag():
        project_dir = Path("/var/graphrag/tennants\gil_fernandes/graphrag/dwell")
        topics = generate_topics(
            TopicsRequest(project_dir=project_dir, engine=Engine.GRAPHRAG)
        )
        return topics

    topics = test_graphrag()
    for topic in topics.topics:
        print(topic.name)
        print(topic.description)
        print(topic.type)
        print(topic.questions)
        print("-" * 100)

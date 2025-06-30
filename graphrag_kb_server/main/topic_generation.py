from pathlib import Path

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import Topics, Topic, TopicsRequest
from graphrag_kb_server.service.lightrag.lightrag_centrality import get_sorted_centrality_scores_as_pd

def generate_topics(topics_request: TopicsRequest) -> Topics:
    match topics_request.engine:
        case Engine.GRAPHRAG:
            return _generate_topics_graphrag(topics_request)
        case Engine.LIGHTRAG:
            return _generate_topics_lightrag(topics_request)
        case _:
            raise ValueError(f"Engine {engine} not supported")


def _generate_topics_graphrag(topics_request: TopicsRequest):
    pass

def _generate_topics_lightrag(topics_request: TopicsRequest) -> Topics:
    centrality_scores = get_sorted_centrality_scores_as_pd(topics_request.project_dir)
    topics = []
    for _, row in centrality_scores[:topics_request.limit].iterrows():
        topics.append(Topic(
            name=row["entity_id"],
            description=row["description"],
            type=row["entity_type"],
            questions=[]
        ))
    return Topics(topics=topics)


if __name__ == "__main__":
    project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
    topics = generate_topics(TopicsRequest(project_dir=project_dir, engine=Engine.LIGHTRAG))
    for topic in topics.topics:
        print(topic.name)
        print(topic.description)
        print(topic.type)
        print(topic.questions)
        print("-" * 100)
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopicsRequest
from graphrag_kb_server.service.graphrag.graph_support import read_graphrag_project
from graphrag_kb_server.service.similar_topics import get_sorted_related_entities_simple_rerank


def get_related_topics_graphrag(request: SimilarityTopicsRequest) -> SimilarityTopics | None:
    G = read_graphrag_project(request.project_dir)
    if not request.source in G.nodes():
        return None
    return get_sorted_related_entities_simple_rerank(G, request)


if __name__ == "__main__":
    from pathlib import Path
    project_dir = Path("/var/graphrag/tennants/gil_fernandes/graphrag/lmo")
    assert project_dir.exists()
    similarity_topics = get_related_topics_graphrag(
        SimilarityTopicsRequest(project_dir=project_dir, source="MEDITATION", engine=Engine.GRAPHRAG)
    )
    if similarity_topics is not None:
        for st in similarity_topics.topics:
            print(st.name, st.probability)
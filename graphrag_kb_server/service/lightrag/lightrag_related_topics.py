from pathlib import Path
import random
from collections import Counter

import networkx as nx

from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopic
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir
)
from graphrag_kb_server.service.similar_topics import (
    get_sorted_related_entities_simple_rerank
)
from graphrag_kb_server.model.topics import SimilarityTopicsRequest

def get_sorted_related_entities(
        project_dir: Path,
        source: str,
        k: int = 8,
        path_length: int = 5) -> SimilarityTopics | None:
    G = create_network_from_project_dir(project_dir)
    if not source in G.nodes():
        return None
    similar_nodes = nx.panther_similarity(G, k=k, c=0.8, source=source, path_length=path_length, weight=None)
    similarity_topics = [(G.nodes()[k], v) for k, v in similar_nodes.items()]
    similarity_topics = sorted(similarity_topics, key=lambda x: x[1], reverse=True)
    
    return SimilarityTopics(topics=[SimilarityTopic(name=st[0]["entity_id"], description=st[0]["description"], type=st[0]["entity_type"], questions=[], probability=st[1]) for st in similarity_topics])


def get_related_topics_lightrag(request: SimilarityTopicsRequest) -> SimilarityTopics | None:
    G = create_network_from_project_dir(request.project_dir)
    if not request.source in G.nodes():
        return None
    return get_sorted_related_entities_simple_rerank(G, request)
    

if __name__ == "__main__":
    project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
    assert project_dir.exists()

    similarity_topics = get_related_topics_lightrag(
        SimilarityTopicsRequest(project_dir=project_dir, source="LLMs"))
    if similarity_topics is not None:
        for st in similarity_topics.topics:
            print(st.name, st.probability)
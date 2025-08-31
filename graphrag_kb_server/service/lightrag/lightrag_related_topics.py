from pathlib import Path

import networkx as nx

from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopic
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
)
from graphrag_kb_server.service.similar_topics import (
    get_sorted_related_entities_simple_rerank,
)
from graphrag_kb_server.model.topics import SimilarityTopicsRequest
from graphrag_kb_server.service.lightrag.lightrag_search import (
    extract_keywords_only_lightrag,
)
from lightrag.base import QueryParam
from graphrag_kb_server.service.topics_post_processing import post_process_topics


def get_sorted_related_entities(
    project_dir: Path, source: str, k: int = 8, path_length: int = 5
) -> SimilarityTopics | None:
    G = create_network_from_project_dir(project_dir)
    if source not in G.nodes():
        return None
    similar_nodes = nx.panther_similarity(
        G, k=k, c=0.8, source=source, path_length=path_length, weight=None
    )
    similarity_topics = [(G.nodes()[k], v) for k, v in similar_nodes.items()]
    similarity_topics = sorted(similarity_topics, key=lambda x: x[1], reverse=True)

    return SimilarityTopics(
        topics=[
            SimilarityTopic(
                name=st[0]["entity_id"],
                description=st[0]["description"],
                type=st[0]["entity_type"],
                questions=[],
                probability=st[1],
            )
            for st in similarity_topics
        ]
    )


async def get_keywords_from_text(
    text: str, project_dir: Path, G: nx.Graph | None = None
) -> list[str]:
    if G is None:
        G = create_network_from_project_dir(project_dir)
    hl_keywords, ll_keywords = await extract_keywords_only_lightrag(
        text, QueryParam(mode="hybrid"), project_dir
    )
    all_keywords = [*hl_keywords, *ll_keywords]
    # Convert nodes to a set for O(1) lookup instead of O(n) for each keyword
    nodes_set = set(G.nodes())
    existing_keywords = [k for k in all_keywords if k in nodes_set]
    return existing_keywords


async def get_related_topics_lightrag(
    request: SimilarityTopicsRequest,
) -> SimilarityTopics | None:
    G = create_network_from_project_dir(request.project_dir)
    if not request.source and request.text:
        existing_keywords = await get_keywords_from_text(
            request.text, request.project_dir, G
        )
        if len(existing_keywords) > 0:
            args = {**request.model_dump(), "source": existing_keywords[0]}
            request = SimilarityTopicsRequest(**args)
        else:
            return None
    if request.source not in G.nodes():
        return None
    similarity_topics = get_sorted_related_entities_simple_rerank(G, request)
    if request.topics_prompt:
        similarity_topics = await post_process_topics(similarity_topics, request.topics_prompt)
    return similarity_topics


if __name__ == "__main__":
    project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
    assert project_dir.exists()

    similarity_topics = get_related_topics_lightrag(
        SimilarityTopicsRequest(project_dir=project_dir, source="LLMs")
    )
    if similarity_topics is not None:
        for st in similarity_topics.topics:
            print(st.name, st.probability)

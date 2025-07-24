import random
from collections import Counter
import numpy as np
import networkx as nx
from graphrag_kb_server.model.topics import (
    SimilarityTopics,
    SimilarityTopic,
    SimilarityTopicsRequest,
)
from graphrag_kb_server.model.engines import Engine


def _prepare_graph_for_numba(
    G: nx.Graph, source: str
) -> tuple[np.ndarray, dict, dict, int]:
    """
    Prepare NetworkX graph for Numba processing.

    Returns:
        (adjacency_matrix, node_to_index, index_to_node, source_index)
    """
    # Create node mappings
    nodes = list(G.nodes())
    node_to_index = {node: i for i, node in enumerate(nodes)}
    index_to_node = {i: node for i, node in enumerate(nodes)}

    # Create adjacency matrix
    n = len(nodes)
    adjacency_matrix = np.zeros((n, n), dtype=np.int32)

    for u, v in G.edges():
        i, j = node_to_index[u], node_to_index[v]
        adjacency_matrix[i][j] = 1
        adjacency_matrix[j][i] = 1  # Undirected graph

    source_index = node_to_index[source]
    return adjacency_matrix, node_to_index, index_to_node, source_index


def convert_to_similarity_topics(
    G: nx.Graph, visited_nodes: list[str], request: SimilarityTopicsRequest
) -> SimilarityTopics:
    # Count node frequencies
    counter = Counter(visited_nodes)
    top_k = counter.most_common(request.k)

    # Convert to similarity topics
    similarity_topics = []
    match request.engine:
        case Engine.GRAPHRAG:
            entity_name_key = "name"
            entity_type_key = "type"
        case Engine.LIGHTRAG:
            entity_name_key = "entity_id"
            entity_type_key = "entity_type"
        case Engine.CAG:
            entity_name_key = "entity_id"
            entity_type_key = "type"

    for node_id, frequency in top_k:
        if node_id in G.nodes():
            node_data = G.nodes()[node_id]
            # Normalize probability by total samples
            probability = frequency / (request.samples * request.path_length)
            similarity_topics.append(
                SimilarityTopic(
                    name=node_data[entity_name_key],
                    description=node_data["description"],
                    type=node_data[entity_type_key],
                    questions=[],
                    probability=probability,
                )
            )

    return SimilarityTopics(topics=similarity_topics)


def get_similar_nodes(
    G: nx.Graph, request: SimilarityTopicsRequest
) -> SimilarityTopics:
    # Use Numba-optimized version for better performance
    visited_nodes = []
    samples, path_length, restart_prob, source = (
        request.samples,
        request.path_length,
        request.restart_prob,
        request.source,
    )
    for _ in range(samples):
        current_node = source
        path = [current_node]

        for _ in range(path_length):
            if random.random() < restart_prob:
                current_node = source
            else:
                neighbors = list(G.neighbors(current_node))
                if not neighbors:
                    break
                current_node = random.choice(neighbors)
                path.append(current_node)

        visited_nodes.extend(path)
    similarity_topics = convert_to_similarity_topics(G, visited_nodes, request)
    return similarity_topics


def get_sorted_related_entities_simple_rerank(
    G: nx.Graph, request: SimilarityTopicsRequest
) -> SimilarityTopics | None:
    similarity_topics_results = []
    for _ in range(request.runs):
        related_entities = get_similar_nodes(G, request)
        if related_entities is None:
            return None
        similarity_topics_results.append(related_entities)
    similarity_topics_results = similarity_topics_results
    return rerank_similarity_topics(similarity_topics_results, request.k)


def rerank_similarity_topics(
    similarity_topics: list[SimilarityTopics], limit: int
) -> SimilarityTopics | None:
    topic_points = {}
    for st in similarity_topics:
        if st is None:
            return None
        for topic in st.topics:
            if topic.name not in topic_points:
                topic_points[topic.name] = (topic, topic.probability)
            else:
                topic_points[topic.name] = (
                    topic,
                    topic_points[topic.name][1] + topic.probability,
                )
    topic_points = sorted(topic_points.items(), key=lambda x: x[1][1], reverse=True)
    topic_points = topic_points[:limit]
    return SimilarityTopics(topics=[tp[1][0] for tp in topic_points])

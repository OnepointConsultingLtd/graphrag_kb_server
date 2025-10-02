from pathlib import Path
import random
from collections import Counter

import networkx as nx
import numpy as np
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from graspologic.embed import node2vec_embed

from graphrag_kb_server.model.topics import (
    SimilarityTopics,
    SimilarityTopic,
    SimilarityTopicsRequest,
)
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.utils.cache import GenericSimpleCache
from graphrag_kb_server.model.related_topics import RelatedTopicsNearestNeighbors
from graphrag_kb_server.model.topics import SimilarityTopicsMethod


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
    neighbors_cache = {}
    visited_nodes = []
    rand = random.random
    randrange = random.randrange
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
            if rand() < restart_prob:
                current_node = source
            else:
                neighbors = neighbors_cache.setdefault(
                    current_node, tuple(G.neighbors(current_node))
                )
                if not neighbors:
                    break
                current_node = neighbors[randrange(len(neighbors))]
                path.append(current_node)

        visited_nodes.extend(path)
    similarity_topics = convert_to_similarity_topics(G, visited_nodes, request)
    return similarity_topics


_nearest_neighbors_cache = GenericSimpleCache[Path, RelatedTopicsNearestNeighbors]()


def _get_nearest_neighbors_vectors(
    G: nx.Graph, project_dir: Path
) -> RelatedTopicsNearestNeighbors:
    nearest_neighbors = _nearest_neighbors_cache.get(project_dir)
    if nearest_neighbors is not None:
        return nearest_neighbors
    nodes: list[str] = list(G.nodes())

    X, vertex_labels = node2vec_embed(G)

    # For undirected graphs, X is (n, d).
    # For directed graphs, X is a tuple (X_in, X_out). Concatenate for a single embedding:
    if isinstance(X, tuple):
        X = np.hstack(X[0])  # shape (n, 2d)

    # --- 4) (Optional) Normalize if you want cosine similarity ---
    X_cos = normalize(X)  # row-wise L2 norm = 1

    # --- 5) Build a k-NN index over the embeddings ---
    # Choose 'cosine' or 'euclidean' to match your intention
    k = 10
    nn = NearestNeighbors(
        metric="cosine", n_neighbors=k + 1
    )  # +1 to include the node itself
    nn.fit(X_cos)

    node_to_idx: dict[str, int] = {u: i for i, u in enumerate(vertex_labels)}

    nearest_neighbors = RelatedTopicsNearestNeighbors(
        node_to_idx=node_to_idx,
        nodes=vertex_labels,
        X=X,
        X_cos=X_cos,
        nn=nn,
    )
    _nearest_neighbors_cache.set(project_dir, nearest_neighbors)
    return nearest_neighbors


def get_similar_nodes_nearest_neighbors(
    G: nx.Graph, request: SimilarityTopicsRequest
) -> SimilarityTopics:
    nearest_neighbors = _get_nearest_neighbors_vectors(G, request.project_dir)
    idx = nearest_neighbors.node_to_idx[request.source]
    query_vec = (
        nearest_neighbors.X_cos[idx : idx + 1]
        if request.use_cosine
        else nearest_neighbors.X[idx : idx + 1]
    )
    dist, ind = nearest_neighbors.nn.kneighbors(query_vec, n_neighbors=request.k + 1)
    ind = ind.ravel()
    dist = dist.ravel()
    ind = ind[1:]
    dist = dist[1:]
    similarity_topics = []
    for i in range(len(ind)):
        node_name = nearest_neighbors.nodes[ind[i]]
        node_data = G.nodes[node_name]
        similarity_topics.append(
            SimilarityTopic(
                name=nearest_neighbors.nodes[ind[i]],
                description=node_data["description"],
                type=node_data["entity_type"],
                questions=[],
                probability=dist[i],
            )
        )
    similarity_topics = sorted(
        similarity_topics, key=lambda x: x.probability, reverse=False
    )
    return SimilarityTopics(topics=similarity_topics)


def get_sorted_related_entities_simple_rerank(
    G: nx.Graph, request: SimilarityTopicsRequest
) -> SimilarityTopics | None:
    similarity_topics_results = []
    match request.method:
        case SimilarityTopicsMethod.RANDOM_WALK:
            for _ in range(request.runs):
                related_entities = get_similar_nodes(G, request)
                if related_entities is None:
                    return None
                similarity_topics_results.append(related_entities)
            return rerank_similarity_topics(similarity_topics_results, request.k)
        case SimilarityTopicsMethod.NEAREST_NEIGHBORS:
            related_entities = get_similar_nodes_nearest_neighbors(G, request)
            return related_entities


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

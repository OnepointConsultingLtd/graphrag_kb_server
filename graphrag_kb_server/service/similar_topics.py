import random
from collections import Counter
import numpy as np
from numba import jit, prange
import networkx as nx
from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopic, SimilarityTopicsRequest
from graphrag_kb_server.model.engines import Engine


@jit(nopython=True, parallel=True)
def _numba_random_walk(
    adjacency_matrix: np.ndarray,
    node_to_index: dict,
    index_to_node: dict,
    source_index: int,
    samples: int,
    path_length: int,
    restart_prob: float,
    rng_seed: int
) -> np.ndarray:
    """
    Numba-optimized random walk implementation.
    
    Args:
        adjacency_matrix: 2D numpy array representing graph adjacency
        node_to_index: Mapping from node IDs to matrix indices
        index_to_node: Mapping from matrix indices to node IDs
        source_index: Index of the source node
        samples: Number of random walks
        path_length: Length of each walk
        restart_prob: Probability of restarting at source
        rng_seed: Random seed for reproducibility
    
    Returns:
        Array of visited node indices (excluding source)
    """
    np.random.seed(rng_seed)
    n_nodes = len(adjacency_matrix)
    visited_nodes = np.zeros(samples * path_length, dtype=np.int32)
    visited_count = 0
    
    for sample in prange(samples):
        current_index = source_index
        
        for step in range(path_length):
            # Check for restart
            if np.random.random() < restart_prob:
                current_index = source_index
            else:
                # Get neighbors
                neighbors = np.where(adjacency_matrix[current_index] > 0)[0]
                if len(neighbors) == 0:
                    break
                # Random choice from neighbors
                current_index = np.random.choice(neighbors)
            
            # Store visited node (excluding source)
            if current_index != source_index:
                visited_nodes[visited_count] = current_index
                visited_count += 1
    
    return visited_nodes[:visited_count]


def _prepare_graph_for_numba(G: nx.Graph, source: str) -> tuple[np.ndarray, dict, dict, int]:
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


def get_similar_nodes_numba(G: nx.Graph, request: SimilarityTopicsRequest) -> SimilarityTopics:
    """
    Numba-optimized version of get_similar_nodes.
    """
    # Prepare graph for Numba
    adjacency_matrix, node_to_index, index_to_node, source_index = _prepare_graph_for_numba(G, request.source)
    
    # Run Numba-optimized random walk
    visited_indices = _numba_random_walk(
        adjacency_matrix=adjacency_matrix,
        node_to_index=node_to_index,
        index_to_node=index_to_node,
        source_index=source_index,
        samples=request.samples,
        path_length=request.path_length,
        restart_prob=request.restart_prob,
        rng_seed=random.randint(0, 2**32 - 1)
    )
    
    # Convert indices back to node IDs
    visited_nodes = [index_to_node[idx] for idx in visited_indices]
    
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
                    probability=probability
                )
            )
    
    return SimilarityTopics(topics=similarity_topics)


def get_similar_nodes(G: nx.Graph, request: SimilarityTopicsRequest) -> SimilarityTopics:
    # Use Numba-optimized version for better performance
    return get_similar_nodes_numba(G, request)


def get_sorted_related_entities_simple_rerank(
        G: nx.Graph,
        request: SimilarityTopicsRequest) -> SimilarityTopics | None:
    similarity_topics_results = []
    for _ in range(request.runs):
        related_entities = get_similar_nodes(G, request)
        if related_entities is None:
            return None
        similarity_topics_results.append(related_entities)
    return rerank_similarity_topics(similarity_topics_results)


def rerank_similarity_topics(similarity_topics: list[SimilarityTopics]) -> SimilarityTopics | None:
    topic_points = {}
    for st in similarity_topics:
        if st is None:
            return None
        for topic in st.topics:
            if topic.name not in topic_points:
                topic_points[topic.name] = (topic, topic.probability)
            else:
                topic_points[topic.name] = (topic, topic_points[topic.name][1] + topic.probability)
    topic_points = sorted(topic_points.items(), key=lambda x: x[1][1], reverse=True)
    return SimilarityTopics(topics=[tp[1][0] for tp in topic_points])


def benchmark_random_walk_performance(G: nx.Graph, request: SimilarityTopicsRequest) -> dict:
    """
    Benchmark the performance difference between original and Numba implementations.
    
    Returns:
        Dictionary with timing results
    """
    import time
    
    # Test original implementation (if we keep it)
    def original_implementation():
        visited_nodes = []
        samples, path_length, restart_prob, source = request.samples, request.path_length, request.restart_prob, request.source
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
            
            visited_nodes.extend(path[1:])
        return visited_nodes
    
    # Time original implementation
    start_time = time.time()
    original_result = original_implementation()
    original_time = time.time() - start_time
    
    # Time Numba implementation
    start_time = time.time()
    numba_result = get_similar_nodes_numba(G, request)
    numba_time = time.time() - start_time
    
    return {
        "original_time": original_time,
        "numba_time": numba_time,
        "speedup": original_time / numba_time,
        "original_nodes_visited": len(original_result),
        "numba_nodes_visited": len(numba_result.topics) if numba_result else 0
    }


if __name__ == "__main__":
    # Simple test to verify the implementation works
    import networkx as nx
    from pathlib import Path
    
    # Create a simple test graph
    G = nx.Graph()
    G.add_edges_from([
        ("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), 
        ("D", "E"), ("E", "F"), ("F", "G"), ("G", "H")
    ])
    
    # Add node attributes
    for node in G.nodes():
        G.nodes[node]["entity_id"] = node
        G.nodes[node]["description"] = f"Description of {node}"
        G.nodes[node]["entity_type"] = "test"
    
    # Test request
    request = SimilarityTopicsRequest(
        project_dir=Path("/tmp/test"),
        source="A",
        samples=1000,
        path_length=3,
        k=5,
        restart_prob=0.15,
        engine=Engine.LIGHTRAG
    )
    
    # Run benchmark
    results = benchmark_random_walk_performance(G, request)
    print(f"Performance Results:")
    print(f"Original time: {results['original_time']:.4f}s")
    print(f"Numba time: {results['numba_time']:.4f}s")
    print(f"Speedup: {results['speedup']:.2f}x")
    print(f"Original nodes visited: {results['original_nodes_visited']}")
    print(f"Numba nodes visited: {results['numba_nodes_visited']}")
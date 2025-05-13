from pathlib import Path
from collections import Counter

import networkx as nx
import rustworkx as rx


def create_network_from_project_dir(project_dir: Path) -> nx.classes.graph.Graph:
    graph_file = project_dir / "lightrag" / "graph_chunk_entity_relation.graphml"
    assert graph_file.exists(), f"Graph file {graph_file} does not exist"
    G = nx.read_graphml(graph_file)
    return G


def networkx_to_rustworkx(nx_graph: nx.Graph) -> rx.PyGraph:
    # Create an empty PyGraph (undirected)
    rw_graph = rx.PyGraph()

    # Add nodes and keep track of node mapping (NetworkX ID → rustworkx node index)
    nx_to_rw_map = {}
    for node in nx_graph.nodes(data=True):
        node_id, node_data = node
        rw_node_index = rw_graph.add_node(node_data)  # store data if needed
        nx_to_rw_map[node_id] = rw_node_index

    # Add edges
    for source, target, edge_data in nx_graph.edges(data=True):
        rw_graph.add_edge(nx_to_rw_map[source], nx_to_rw_map[target], edge_data)

    return rw_graph


def extract_entity_types(graph: nx.classes.graph.Graph) -> dict[str, int]:
    entity_types = Counter()
    for node in graph.nodes(data=True):
        entity_types[node[1]["entity_type"]] += 1
    return dict(entity_types)


if __name__ == "__main__":

    clustre1 = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre1")
    G = create_network_from_project_dir(clustre1)
    entity_types = extract_entity_types(G)
    for entity_type, count in entity_types.items():
        print(f"{entity_type}: {count}")

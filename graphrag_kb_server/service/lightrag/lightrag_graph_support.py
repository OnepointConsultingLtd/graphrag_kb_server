from pathlib import Path
from collections import Counter
import json
from io import BytesIO

import pandas as pd

import networkx as nx
import rustworkx as rx

from graphrag_kb_server.model.community import Community
from graphrag_kb_server.model.graph import CommunityReport
from graphrag_kb_server.utils.cache import GenericSimpleCache


graph_cache = GenericSimpleCache[nx.classes.graph.Graph, Path]()


def create_network_from_project_dir(project_dir: Path) -> nx.classes.graph.Graph:
    graph = graph_cache.get(project_dir)
    if graph is not None:
        return graph
    graph_file = project_dir / "lightrag" / "graph_chunk_entity_relation.graphml"
    assert graph_file.exists(), f"Graph file {graph_file} does not exist"
    G = nx.read_graphml(graph_file)
    graph_cache.set(project_dir, G)
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


def extract_entity_types_excel(graph: nx.classes.graph.Graph) -> bytes:
    entity_counts = extract_entity_types(graph)
    df = pd.DataFrame(
        [(k, v) for k, v in entity_counts.items()], columns=["entity_type", "count"]
    )
    # Create BytesIO buffer
    buffer = BytesIO()
    df.to_excel(buffer, index=True, header=True)
    return buffer.getvalue()


def create_network_from_communities(
    communities: list[Community],
) -> nx.classes.graph.Graph:
    graph = nx.DiGraph()
    nodes = []
    edges = []
    for community in communities:
        nodes.append(
            (
                community.cluster_id,
                {
                    "id": community.cluster_id,
                    "label": community.name,
                    "description": community.community_description,
                    "level": community.level,
                    "number_of_nodes": community.number_of_nodes,
                    "nodes": json.dumps(community.nodes),
                },
            )
        )
        if community.parent_cluster_id != -1:
            edges.append((community.cluster_id, community.parent_cluster_id))
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    return graph


async def create_communities_gexf_for_project(
    project_dir: Path, max_cluster_size: int = 500, recreate: bool = False
) -> Path:
    gexf_file = project_dir / f"communities_{max_cluster_size}.gexf"
    if gexf_file.exists() and not recreate:
        return gexf_file
    from graphrag_kb_server.service.lightrag.lightrag_clustering import (
        cluster_graph_from_project_dir,
    )

    communities = await cluster_graph_from_project_dir(project_dir, max_cluster_size)
    graph = create_network_from_communities(communities)
    nx.write_gexf(graph, gexf_file)
    return gexf_file


async def find_community_lightrag(
    project_dir: Path, community_id: str
) -> CommunityReport | None:
    gexf_file = await create_communities_gexf_for_project(project_dir)
    graph = nx.read_gexf(gexf_file)
    node = graph.nodes.get(community_id)
    if not node:
        return None
    community_report = CommunityReport(
        id=int(community_id),
        title=node["label"],
        summary=node["description"],
    )
    return community_report


if __name__ == "__main__":
    import asyncio

    project_dir = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre1")

    def test_create_network_from_project_dir():
        G = create_network_from_project_dir(project_dir)
        entity_types = extract_entity_types(G)
        for entity_type, count in entity_types.items():
            print(f"{entity_type}: {count}")

    def test_create_network_from_communities():
        gexf_file = asyncio.run(create_communities_gexf_for_project(project_dir))
        assert gexf_file.exists()

    def test_find_community_lightrag():
        community_report = asyncio.run(find_community_lightrag(project_dir, "15"))
        assert community_report is not None
        print(community_report)

    def test_extract_entity_types_excel():
        G = create_network_from_project_dir(project_dir)
        entity_types = extract_entity_types_excel(G)
        with open("entity_types.xlsx", "wb") as f:
            f.write(entity_types)

    def test_connected_components():
        G = create_network_from_project_dir(project_dir)
        connected_components = [
            c for c in sorted(nx.connected_components(G), key=len, reverse=True)
        ]
        data = []
        for cc in connected_components:
            print(f"{len(cc)}: {cc}")
            data.append((len(cc), cc))
        df = pd.DataFrame(data, columns=["size", "nodes"])
        df.index = range(1, len(df) + 1)
        df.to_excel("connected_components_1.xlsx", index=True, header=True)

    test_connected_components()

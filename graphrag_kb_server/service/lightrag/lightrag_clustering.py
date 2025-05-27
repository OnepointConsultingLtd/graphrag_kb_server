from pathlib import Path
from typing import Any, cast
import html
import datetime
import pandas as pd

from graspologic.utils import largest_connected_component
import networkx as nx

from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.community import Community, CommunityDescriptors
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
)
from google import genai
from graphrag_kb_server.config import cfg, lightrag_cfg

Communities = list[Community]

NodeIdToCommunityMap = dict[int, dict[str, int]]
ParentMapping = dict[int, int]


async def cluster_graph_from_project_dir(
    project_dir: Path, lightrag_max_cluster_size: int = 10
) -> Communities:
    graph = create_network_from_project_dir(project_dir)
    communities = _cluster_graph(graph, lightrag_max_cluster_size, True, 42)
    client = genai.Client(api_key=cfg.gemini_api_key)
    for index, community in enumerate(communities):
        logger.info(
            f"Generating community report for community {index + 1} of {len(communities)}"
        )
        community_descriptors: CommunityDescriptors = await _generate_community_report(
            graph, community, client
        )
        community.name = community_descriptors.name
        community.community_description = community_descriptors.community_description
        community.node_descriptions = community_descriptors.node_descriptions

    return communities


def generate_communities_dataframe(communities: Communities) -> pd.DataFrame:
    if len(communities) == 0:
        return pd.DataFrame()
    return pd.DataFrame(
        [community.model_dump() for community in communities],
        columns=list(communities[0].model_fields.keys()),
    )


async def generate_communities_excel(
    project_dir: Path, lightrag_max_cluster_size: int = 10
) -> Path:
    communities_file = (
        project_dir
        / f"communities_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    )
    communities = await cluster_graph_from_project_dir(
        project_dir, lightrag_max_cluster_size
    )
    df = generate_communities_dataframe(communities)
    df.index = range(1, len(df) + 1)
    df.to_excel(communities_file, index=True)
    return communities_file


async def _generate_community_report(
    graph: nx.classes.graph.Graph, community: Community, client: genai.Client
) -> CommunityDescriptors:
    nodes_data = graph.nodes(data=True)
    nodes_data_list = []
    for node in community.nodes:
        node_data = nodes_data[node]
        nodes_data_list.append(
            f"""- {node}
type: {node_data['entity_type']}
description: {node_data['description']}
"""
        )
    nodes_data_str = "\n".join(nodes_data_list)
    prompt = f"""
You are a helpful assistant that generates a report for a community in a graph.
The community is represented by a list of nodes and can be found between the <community> tags.

<community>
{nodes_data_str}
</community>

The report should be a short description of the community, including a description of the most important nodes in the community and their relationships.

    """
    response = client.models.generate_content(
        model=lightrag_cfg.lightrag_model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": CommunityDescriptors,
        },
    )
    return response.parsed


def _cluster_graph(
    graph: nx.classes.graph.Graph,
    max_cluster_size: int,
    use_largest_connected_component: bool,
    seed: int | None = None,
) -> Communities:
    if len(graph.nodes) == 0:
        logger.warning("Graph has no nodes")
        return []
    node_id_to_community_map, parent_mapping = _compute_leiden_communities(
        graph, max_cluster_size, use_largest_connected_component, seed
    )
    levels = sorted(node_id_to_community_map.keys())

    clusters: dict[int, dict[int, list[str]]] = {}
    for level in levels:
        result = {}
        clusters[level] = result
        for node_id, raw_community_id in node_id_to_community_map[level].items():
            community_id = raw_community_id
            if community_id not in result:
                result[community_id] = []
            result[community_id].append(node_id)

    results: Communities = []
    for level in clusters:
        for cluster_id, nodes in clusters[level].items():
            community = Community(
                level=level,
                cluster_id=cluster_id,
                parent_cluster_id=parent_mapping[cluster_id],
                nodes=nodes,
                number_of_nodes=len(nodes),
            )
            results.append(community)
    results = sorted(results, key=lambda x: x.number_of_nodes, reverse=True)
    return results


def _compute_leiden_communities(
    graph: nx.Graph | nx.DiGraph,
    max_cluster_size: int,
    use_largest_connected_component: bool,
    seed: int | None = None,
) -> tuple[NodeIdToCommunityMap, ParentMapping]:
    """Return Leiden root communities and their hierarchy mapping."""
    # NOTE: This import is done here to reduce the initial import time of the graphrag package
    from graspologic.partition import hierarchical_leiden

    if use_largest_connected_component:
        graph = _stable_largest_connected_component(graph)

    community_mapping = hierarchical_leiden(
        graph, max_cluster_size=max_cluster_size, random_seed=seed
    )
    results: NodeIdToCommunityMap = {}
    hierarchy: ParentMapping = {}

    no_parent = -1
    for partition in community_mapping:
        results[partition.level] = results.get(partition.level, {})
        results[partition.level][partition.node] = partition.cluster
        hierarchy[partition.cluster] = (
            partition.parent_cluster if partition.parent_cluster else no_parent
        )
    return results, hierarchy


def _stable_largest_connected_component(graph: nx.Graph) -> nx.Graph:
    """
    Return the largest connected component of the graph, with nodes and edges sorted in a stable way.
    This was copied from GraphRAG.
    """
    # NOTE: The import is done here to reduce the initial import time of the module

    graph = graph.copy()
    graph = cast("nx.Graph", largest_connected_component(graph))
    graph = normalize_node_names(graph)
    return _stabilize_graph(graph)


def _stabilize_graph(graph: nx.Graph) -> nx.Graph:
    """
    Ensure an undirected graph with the same relationships will always be read the same way.
    This was copied from GraphRAG.
    """
    fixed_graph = nx.DiGraph() if graph.is_directed() else nx.Graph()

    sorted_nodes = sorted(graph.nodes(data=True), key=lambda x: x[0])
    fixed_graph.add_nodes_from(sorted_nodes)

    edges = list(graph.edges(data=True))

    # If the graph is undirected, we create the edges in a stable way, so we get the same results
    # for example:
    # A -> B
    # in graph theory is the same as
    # B -> A
    # in an undirected graph
    # however, this can lead to downstream issues because sometimes
    # consumers read graph.nodes() which ends up being [A, B] and sometimes it's [B, A]
    # but they base some of their logic on the order of the nodes, so the order ends up being important
    # so we sort the nodes in the edge in a stable way, so that we always get the same order

    if not graph.is_directed():

        def _sort_source_target(edge):
            source, target, edge_data = edge
            if source > target:
                temp = source
                source = target
                target = temp
            return source, target, edge_data

        edges = [_sort_source_target(edge) for edge in edges]

    def _get_edge_key(source: Any, target: Any) -> str:
        return f"{source} -> {target}"

    edges = sorted(edges, key=lambda x: _get_edge_key(x[0], x[1]))

    fixed_graph.add_edges_from(edges)

    return fixed_graph


def normalize_node_names(graph: nx.Graph | nx.DiGraph) -> nx.Graph | nx.DiGraph:
    """Normalize node names."""
    node_mapping = {node: html.unescape(node.strip()) for node in graph.nodes()}  # type: ignore
    return nx.relabel_nodes(graph, node_mapping)


if __name__ == "__main__":
    import asyncio

    project_dir = (
        Path(__file__).parent.parent.parent.parent
        / "docs/dummy_projects/lightrag/dwell1"
    )
    assert project_dir.exists()
    communities = asyncio.run(cluster_graph_from_project_dir(project_dir, 10))
    df = generate_communities_dataframe(communities)
    df.to_excel("communities.xlsx", index=True)

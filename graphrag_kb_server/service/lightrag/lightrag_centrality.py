from pathlib import Path

import pandas as pd
import rustworkx as rx

from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
    networkx_to_rustworkx,
)


def get_sorted_centrality_scores(
    project_dir: Path,
) -> list[tuple[str, str, str, str, float]]:
    G = create_network_from_project_dir(project_dir)
    rw_graph = networkx_to_rustworkx(G)
    centrality = rx.betweenness_centrality(rw_graph)
    node_centrality = {
        node: (centrality[node], rw_graph[node]) for node in rw_graph.node_indices()
    }
    sorted_centrality = []
    for _, centrality_info in sorted(
        node_centrality.items(), key=lambda item: item[1][0], reverse=True
    ):
        data = centrality_info[1]
        sorted_centrality.append(
            (
                data["entity_id"],
                data["entity_type"],
                data["description"],
                data["file_path"],
                centrality_info[0],
            )
        )
    return sorted_centrality


def get_sorted_centrality_scores_as_pd(project_dir: Path) -> pd.DataFrame:
    sorted_centrality = get_sorted_centrality_scores(project_dir)
    data = pd.DataFrame(
        sorted_centrality,
        columns=["entity_id", "entity_type", "description", "file_path", "centrality"],
    )
    data.index = range(1, len(data) + 1)
    return data


if __name__ == "__main__":

    clustre1 = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre1")
    scores = get_sorted_centrality_scores_as_pd(clustre1)
    scores.to_excel("clustre1_centrality.xlsx", index=True, header=True)

from io import BytesIO
from pathlib import Path

import pandas as pd
import rustworkx as rx

from graphrag_kb_server.utils.cache import PersistentSimpleCache

from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
    networkx_to_rustworkx,
)
from graphrag_kb_server.model.node_centrality import NodeCentrality

# Full day cache
lightrag_cache = PersistentSimpleCache[pd.DataFrame]("lightrag_centrality")


def get_sorted_centrality_scores(
    project_dir: Path,
) -> list[NodeCentrality]:
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
    cached_data = lightrag_cache.get(project_dir)
    if cached_data is not None:
        return cached_data
    sorted_centrality = get_sorted_centrality_scores(project_dir)
    data = pd.DataFrame(
        sorted_centrality,
        columns=["entity_id", "entity_type", "description", "file_path", "centrality"],
    )
    data.index = range(1, len(data) + 1)
    lightrag_cache.set(project_dir, data)
    return data


def get_sorted_centrality_scores_as_xls(project_dir: Path, limit: int = -1) -> bytes:
    data = get_sorted_centrality_scores_as_pd(project_dir)
    if limit > 0:
        data = data.head(limit)
    # Create BytesIO buffer
    buffer = BytesIO()
    data.to_excel(buffer, index=True, header=True)
    return buffer.getvalue()


if __name__ == "__main__":

    clustre1 = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre1")
    assert clustre1.exists()
    scores = get_sorted_centrality_scores_as_pd(clustre1)
    scores.to_excel("clustre1_centrality.xlsx", index=True, header=True)

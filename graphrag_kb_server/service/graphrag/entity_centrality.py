from pathlib import Path
import pandas as pd

import rustworkx as rx

from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    networkx_to_rustworkx,
)
from graphrag_kb_server.utils.cache import PersistentSimpleCache
from graphrag_kb_server.model.node_centrality import NodeCentrality
from graphrag_kb_server.service.graphrag.graph_support import read_graphrag_project


_graphrag_centrality_cache = PersistentSimpleCache[pd.DataFrame]("graphrag_centrality")


def _get_entity_centrality(project_dir: Path) -> list[NodeCentrality]:
    G = read_graphrag_project(project_dir)
    rw_graph = networkx_to_rustworkx(G)
    centrality = rx.betweenness_centrality(rw_graph)
    # entity_id, entity_type, description, file_path, centrality_score
    node_centrality = []
    for node in rw_graph.node_indices():
        node_data = rw_graph[node]
        node_centrality.append(
            (
                node_data["name"],
                node_data["type"],
                node_data["description"],
                node_data["file_path"],
                centrality[node],
            )
        )
    node_centrality.sort(key=lambda x: x[4], reverse=True)
    return node_centrality


def get_entity_centrality_as_pd(project_dir: Path) -> pd.DataFrame:
    df = _graphrag_centrality_cache.get(project_dir)
    if df is not None:
        return df
    node_centrality = _get_entity_centrality(project_dir)
    df = pd.DataFrame(
        node_centrality,
        columns=["entity_id", "entity_type", "description", "file_path", "centrality"],
    )
    _graphrag_centrality_cache.set(project_dir, df)
    return df


if __name__ == "__main__":
    project_dir = Path("/var/graphrag/tennants/gil_fernandes/graphrag/lmo")
    node_centrality_df = get_entity_centrality_as_pd(project_dir)
    node_centrality_df.to_csv(
        project_dir / "output" / "entity_centrality.csv", index=False
    )

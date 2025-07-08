from pathlib import Path
import pandas as pd

import networkx as nx
import rustworkx as rx

from graphrag_kb_server.service.graphrag.query import (
    ENTITY_TABLE,
    RELATIONSHIP_TABLE,
    TEXT_UNIT_TABLE,
    DOCUMENTS_TABLE,
)
from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    networkx_to_rustworkx,
)
from graphrag_kb_server.utils.cache import PersistentSimpleCache
from graphrag_kb_server.model.node_centrality import NodeCentrality


_graphrag_centrality_cache = PersistentSimpleCache[pd.DataFrame]("graphrag_centrality")


def _get_entity_centrality(project_dir: Path) -> list[NodeCentrality]:
    output = project_dir / "output"
    entity_df = pd.read_parquet(output / f"{ENTITY_TABLE}.parquet")
    relationship_df = pd.read_parquet(output / f"{RELATIONSHIP_TABLE}.parquet")
    text_unit_df = pd.read_parquet(output / f"{TEXT_UNIT_TABLE}.parquet")
    document_df = pd.read_parquet(output / f"{DOCUMENTS_TABLE}.parquet")
    G = nx.Graph()
    # Create a dictionary mapping node IDs to their data
    node_data = {}
    for title, type, description, text_unit_ids in zip(
        entity_df["title"],
        entity_df["type"],
        entity_df["description"],
        entity_df["text_unit_ids"],
    ):
        file_paths = []
        for text_unit_id in text_unit_ids:
            text_unit = text_unit_df[text_unit_df["id"] == text_unit_id]
            document_ids = text_unit["document_ids"]
            for document_array in document_ids:
                for document_id in document_array:
                    document = document_df[document_df["id"] == document_id]
                    file_paths.append(document["title"].values[0])
        node_data[title] = {
            "name": title,
            "type": type,
            "description": description,
            "file_path": file_paths[0] if len(file_paths) > 0 else "",
        }
    G.add_nodes_from(node_data.items())
    for s, t in zip(relationship_df["source"], relationship_df["target"]):
        G.add_edge(s, t)
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

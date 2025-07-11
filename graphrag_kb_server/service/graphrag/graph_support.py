from pathlib import Path

import networkx as nx
import pandas as pd

from graphrag_kb_server.service.graphrag.query import (
    ENTITY_TABLE,
    RELATIONSHIP_TABLE,
    TEXT_UNIT_TABLE,
    DOCUMENTS_TABLE,
)


def read_graphrag_project(project_dir: Path) -> nx.Graph:
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
    return G



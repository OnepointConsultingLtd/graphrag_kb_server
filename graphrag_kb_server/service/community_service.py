from pathlib import Path

import pandas as pd
import networkx as nx

from graphrag_kb_server.service.query import COMMUNITY_REPORT_TABLE, COMMUNITY_TABLE
from graphrag_kb_server.model.graph import CommunityReport


def prepare_community_extraction(
    project_dir: Path, levels: list[int] | None = [0]
) -> pd.DataFrame:
    output = f"{project_dir}/output"

    community_report_df = pd.read_parquet(f"{output}/{COMMUNITY_REPORT_TABLE}.parquet")
    community_df = pd.read_parquet(f"{output}/{COMMUNITY_TABLE}.parquet")
    merged_df = community_df[["id", "community", "parent", "title", "level"]].merge(
        community_report_df[["id", "community", "title", "summary", "rank"]],
        on=["community"],
    )
    merged_simple_df = merged_df[
        ["community", "parent", "title_y", "level", "summary", "rank"]
    ]
    if levels is not None:
        merged_simple_df = merged_simple_df[merged_simple_df["level"].isin(levels)]
    return merged_simple_df.sort_values(by="rank", ascending=False)


def generate_digraph(project_dir: Path) -> nx.DiGraph:
    df_merged_simple = prepare_community_extraction(project_dir, None)
    G = nx.DiGraph()
    nodes = []
    edges = []
    labels = {}
    for community, parent, title in zip(
        df_merged_simple["community"],
        df_merged_simple["parent"],
        df_merged_simple["title_y"],
    ):
        nodes.append(community)
        if parent > 0:
            edges.append((community, parent))
        labels[community] = title[:50]
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    for n in nodes:
        G.nodes[n]["label"] = labels[n]
    return G


def generate_gexf_file(project_dir: Path) -> Path:
    G = generate_digraph(project_dir)
    generated_file = project_dir / "output/communities.gexf"
    nx.write_gexf(G, generated_file)
    return generated_file


def find_community(project_dir: Path, id: str | int) -> CommunityReport | None:
    community_df = prepare_community_extraction(project_dir, levels=None)
    id = int(id)
    community_dict = community_df[community_df['community'] == id].to_dict()
    summary_res = community_dict['summary']
    if len(summary_res) == 0:
        return None
    title_res = community_dict['title_y']
    return CommunityReport(id=id, title=title_res[id], summary=summary_res[id])


if __name__ == "__main__":
    from graphrag_kb_server.config import cfg

    graphrag_root_dir_path = cfg.graphrag_root_dir_path
    assert (
        graphrag_root_dir_path.exists()
    ), "Cannot find the root directory of GraphRAG Server"

    project_dir: Path | None = None
    for f in graphrag_root_dir_path.rglob("**/*.parquet"):
        if (
            f.is_file()
            and f.stem == COMMUNITY_REPORT_TABLE
            or f.stem == COMMUNITY_TABLE
        ):
            project_dir = f.parent / ".."
            break
    assert project_dir is not None, "There are no projects available"
    assert project_dir.exists(), "Directory does not exist"
    community_df = prepare_community_extraction(project_dir)
    assert community_df is not None, "There should be a community dataframe."
    assert len(community_df) > 0, "There are no entries."
    generated_file = generate_gexf_file(project_dir)
    assert generated_file.exists(), "Nexf file does not exist."

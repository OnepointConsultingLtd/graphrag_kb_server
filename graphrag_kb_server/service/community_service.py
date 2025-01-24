from pathlib import Path

import pandas as pd

from graphrag_kb_server.service.query import COMMUNITY_REPORT_TABLE, COMMUNITY_TABLE


def prepare_community_extraction(
    project_dir: Path, levels: list[int] = [0]
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
    return merged_simple_df[merged_simple_df["level"].isin(levels)].sort_values(
        by="rank", ascending=False
    )


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
    for c in zip(
        community_df["title_y"],
        community_df["summary"],
        community_df["rank"],
        community_df["level"],
    ):
        print(c)

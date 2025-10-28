from io import BytesIO
from pathlib import Path
import asyncio

import pandas as pd
import rustworkx as rx


from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
    networkx_to_rustworkx,
)
from graphrag_kb_server.model.node_centrality import NodeCentrality
from graphrag_kb_server.service.db.db_persistence_topics_centrality import (
    find_topics_with_centrality_by_project_name,
    insert_topics_with_centrality,
)
from graphrag_kb_server.logger import logger


async def get_sorted_centrality_scores(
    project_dir: Path,
) -> list[NodeCentrality]:
    logger.info(f"Getting sorted centrality scores for project: {project_dir}")
    G = await asyncio.to_thread(create_network_from_project_dir, project_dir)
    logger.info(f"Created network from project directory: {project_dir}")
    rw_graph = await asyncio.to_thread(networkx_to_rustworkx, G)
    logger.info(f"Converted network to rustworkx graph: {project_dir}")
    centrality = await asyncio.to_thread(rx.betweenness_centrality, rw_graph)
    logger.info(f"Calculated betweenness centrality for project: {project_dir}")

    def process_centrality_data():
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

    sorted_centrality = await asyncio.to_thread(process_centrality_data)
    logger.info(f"Sorted centrality scores for project: {project_dir}")
    return sorted_centrality


async def convert_to_pd(sorted_centrality: list[NodeCentrality]) -> pd.DataFrame:
    return await asyncio.to_thread(
        lambda: pd.DataFrame(
            sorted_centrality,
            columns=[
                "entity_id",
                "entity_type",
                "description",
                "file_path",
                "centrality",
            ],
        ).set_index(pd.RangeIndex(1, len(sorted_centrality) + 1))
    )


async def get_sorted_centrality_scores_as_pd(project_dir: Path) -> pd.DataFrame:
    logger.info(
        f"Getting sorted centrality scores as pandas dataframe for project: {project_dir}"
    )
    cached_data = await find_topics_with_centrality_by_project_name(project_dir, -1)
    if cached_data is not None and len(cached_data) > 0:
        logger.info(f"Found cached centrality scores for project: {project_dir}")
        return await convert_to_pd(cached_data)
    sorted_centrality = await get_sorted_centrality_scores(project_dir)
    logger.info(f"Sorted centrality scores for project: {project_dir}")
    data = await convert_to_pd(sorted_centrality)
    await insert_topics_with_centrality(project_dir, sorted_centrality)
    logger.info(f"Inserted centrality scores for project: {project_dir}")
    return data


async def get_sorted_centrality_scores_as_xls(
    project_dir: Path, limit: int = -1
) -> bytes:
    data = await get_sorted_centrality_scores_as_pd(project_dir)
    if limit > 0:
        data = data.head(limit)
    # Create BytesIO buffer
    buffer = BytesIO()
    data.to_excel(buffer, index=True, header=True)
    return buffer.getvalue()


if __name__ == "__main__":
    import asyncio

    clustre1 = Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre1")
    assert clustre1.exists()
    scores = asyncio.run(get_sorted_centrality_scores_as_pd(clustre1))
    scores.to_excel("clustre1_centrality.xlsx", index=True, header=True)

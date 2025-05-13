from pathlib import Path

from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores,
)


def test_get_sorted_centrality_scores():
    project_dir = (
        Path(__file__).parent.parent.parent.parent
        / "docs/dummy_projects/lightrag/dwell1"
    )
    scores = get_sorted_centrality_scores(project_dir)
    assert len(scores) > 0

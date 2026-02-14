from pathlib import Path


def test_lightrag_summary():
    from graphrag_kb_server.service.lightrag.lightrag_summary import get_summary
    project_dir = Path(__file__).parent.parent.parent.parent / "data"
    assert project_dir.exists()
    summary = get_summary(
        project_dir,
        "/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/input/clustre/Articles and PoVs/AI_or_Die_-_Generic.txt",
    )
    assert isinstance(summary, str)
    assert summary is not None, "Cannot find summary"

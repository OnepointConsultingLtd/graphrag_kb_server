from pathlib import Path
from graphrag_kb_server.service.lightrag.lightrag_visualization import generate_lightrag_graph_visualization


def test_lightrag_visualization():
    test_dir = Path(__file__).parent.parent.parent.parent / "docs/dummy_projects/lightrag/dwell1"
    assert test_dir.exists()
    output_path = generate_lightrag_graph_visualization(test_dir)
    assert output_path.exists()
    assert output_path.is_file()
    assert output_path.suffix == ".html"

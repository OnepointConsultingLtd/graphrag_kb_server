from pathlib import Path
from graphrag_kb_server.service.zip_service import zip_input
from graphrag_kb_server.config import cfg


def test_zip_input():
    input_folder: Path = cfg.graphrag_root_dir_path / "fake_input"
    input_folder.mkdir(exist_ok=True)
    with open(input_folder / "file1.txt", "wt") as f:
        f.write("Test")
    result = zip_input(input_folder)
    assert result is not None, "There is no result."
    assert result.exists(), "The file does not exist."

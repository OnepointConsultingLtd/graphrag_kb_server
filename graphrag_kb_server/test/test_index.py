import asyncio
import shutil
import tempfile

from pathlib import Path
from graphrag_kb_server.service.index import override_settings, acreate_graph_rag
from graphrag_kb_server.config import cfg
from graphrag_kb_server.service.index import clear_rag


def test_override_settings():
    settings_dir = Path(__file__) / "../../../docs/settings"
    assert settings_dir.exists(), "Input directory does not exist."
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        target = tmp_path / "settings.yaml"
        shutil.copyfile(settings_dir / "settings.yaml", target)
        override_settings(tmp_path)
        assert cfg.openai_api_model_embedding in target.read_text()


def test_acreate_graph_rag():
    clear_rag()
    result = asyncio.run(acreate_graph_rag(create_if_not_exists=False))
    assert result

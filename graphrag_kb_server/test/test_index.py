import shutil
import tempfile

from pathlib import Path
from graphrag_kb_server.service.index import override_settings
from graphrag_kb_server.config import cfg


def test_override_settings():
    settings_dir = Path(__file__) / "../../../docs/settings"
    assert settings_dir.exists(), "Input directory does not exist."
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        target = tmp_path / "settings.yaml"
        shutil.copyfile(settings_dir / "settings.yaml", target)
        override_settings(tmp_path)
        assert cfg.openai_api_model_embedding in target.read_text()

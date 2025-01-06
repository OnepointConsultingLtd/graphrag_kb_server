import asyncio
import shutil
import tempfile

from pathlib import Path
from graphrag_kb_server.service.project import (
    override_settings,
    acreate_graph_rag,
    list_projects,
)
from graphrag_kb_server.config import cfg
from graphrag_kb_server.service.project import clear_rag


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


def test_list_projects():
    projects_dir = Path(__file__) / "../../../docs/dummy_projects"
    assert projects_dir.exists(), "The projects directory does not exist."
    project_listing = list_projects(projects_dir)
    assert project_listing is not None, "There is not project listing."
    assert len(project_listing.projects) > 0, "There should be at least one project"
    for p in project_listing.projects:
        assert len(p.input_files) > 0, "The test project should have at least one file."

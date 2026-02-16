from pathlib import Path

from graphrag_kb_server.model.project import IndexingStatus


def test_write_project_file():
    from graphrag_kb_server.service.project import write_project_file

    project_dir = (
        Path(__file__).parent.parent.parent.parent
        / "docs/dummy_projects/lightrag/dwell1"
    )
    assert project_dir.exists(), f"Project directory does not exist: {project_dir}"
    project = write_project_file(project_dir, IndexingStatus.COMPLETED)
    assert project.name == "dwell1"
    assert project.indexing_status == IndexingStatus.COMPLETED
    assert len(project.input_files) > 0
    assert any([f for f in project.input_files if f.endswith("AIGovernance.txt")])


def test_single_project_status():
    from graphrag_kb_server.service.project import single_project_status

    project_dir = (
        Path(__file__).parent.parent.parent.parent
        / "docs/dummy_projects/lightrag/dwell1"
    )
    assert project_dir.exists(), f"Project directory does not exist: {project_dir}"
    project = single_project_status(project_dir)
    assert project.name == "dwell1"
    assert project.indexing_status == IndexingStatus.COMPLETED or IndexingStatus.UNKNOWN
    assert len(project.input_files) > 0

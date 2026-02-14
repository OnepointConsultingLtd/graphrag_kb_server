from pathlib import Path



def test_list_projects():

    from graphrag_kb_server.service.project import (
        list_projects,
    )

    projects_dir = Path(__file__) / "../../../docs/dummy_projects"
    assert projects_dir.exists(), "The projects directory does not exist."
    engine_project_listing = list_projects(projects_dir)
    assert engine_project_listing is not None, "There is not project listing."
    assert (
        len(engine_project_listing.lightrag_projects.projects) >= 0
    ), "There should be at least one project"
    for p in engine_project_listing.lightrag_projects.projects:
        assert (
            len(p.input_files) >= 0
        ), "The test project should have at least one file."

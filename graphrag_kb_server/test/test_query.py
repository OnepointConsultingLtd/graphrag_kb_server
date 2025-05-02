import pytest
import asyncio
from pathlib import Path
from graphrag_kb_server.service.query import (
    prepare_vector_store,
    load_project_data,
    build_local_context_builder,
    rag_local,
)
from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.rag_parameters import ContextParameters
from graphrag_kb_server.model.context import Search


# Define a fixture for resource initialization
@pytest.fixture
def project_directory():
    # Code to create or initialize your resource
    project_dir = Path(__file__) / "../../../data/onepoint"
    assert project_dir.exists(), "Project directory does not exist"

    yield project_dir  # The test will have access to this resource object

    # Code to clean up the resource if necessary
    print("Tearing down resource...")
    project_dir = None


def test_load_data_remote(project_directory: Path, search: Search = Search.LOCAL):
    _, default_entity_description_table_df = prepare_vector_store(project_directory)
    reports, entities, communities, _ = load_project_data(
        project_directory, search
    )
    assert reports is not None, "Reports are None"
    assert entities is not None, "Entities are None"
    assert len(reports) > 0, "There are no reports"
    assert len(entities) > 0, "There are no entities"


def test_load_data_local(project_directory: Path):
    test_load_data_remote(project_directory)


def test_load_data_drift(project_directory: Path):
    test_load_data_remote(project_directory, Search.DRIFT)


def test_build_local_context_builder(project_directory: Path):
    context = build_local_context_builder(project_directory)
    assert context is not None, "context is None"


def test_rag_local(project_directory: Path):
    context_params = ContextParameters(
        query="What is the value of questions?",
        project_dir=project_directory,
        context_size=cfg.local_context_max_tokens,
    )
    response = asyncio.run(rag_local(context_params))
    assert response is not None, "There is no responses"

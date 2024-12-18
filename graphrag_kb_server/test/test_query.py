import pytest
import asyncio

from graphrag_kb_server.service.query import (
    prepare_vector_store,
    load_project_data,
    build_local_context_builder,
    rag_local,
)
from graphrag_kb_server.service.index import create_graph_rag, GenerationStatus
from graphrag_kb_server.config import cfg
from graphrag_kb_server.model.rag_parameters import ContextParameters


# Define a fixture for resource initialization
@pytest.fixture
def resource_setup():
    # Code to create or initialize your resource
    resource = create_graph_rag(create_if_not_exists=True)

    yield resource  # The test will have access to this resource object

    # Code to clean up the resource if necessary
    print("Tearing down resource...")
    resource = None


def test_load_data(resource_setup: GenerationStatus):
    assert resource_setup is not None
    _, default_entity_description_table_df = prepare_vector_store()
    reports, entities, communities = load_project_data(
        cfg.graphrag_root_dir_path, default_entity_description_table_df
    )
    assert reports is not None, "Reports are None"
    assert entities is not None, "Entities are None"
    assert len(reports) > 0, "There are no reports"
    assert len(entities) > 0, "There are no entities"


def test_build_local_context_builder(resource_setup: GenerationStatus):
    assert resource_setup is not None
    context = build_local_context_builder(cfg.graphrag_root_dir_path)
    assert context is not None, "context is None"


def test_rag_local(resource_setup: GenerationStatus):
    assert resource_setup is not None
    context_params = ContextParameters(
        query="What is the value of questions?",
        project_dir=cfg.graphrag_root_dir_path,
        context_size=cfg.local_context_max_tokens,
    )
    response = asyncio.run(rag_local(context_params))
    assert response is not None, "There is no responses"



from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.rag_parameters import QueryParameters, ContextParameters
from graphrag_kb_server.service.graphrag.prompt_factory import inject_system_prompt_to_query_params
from pathlib import Path


def test_inject_system_prompt_to_query_params():
    instruction = "You are a helpful assistant that can answer questions about the capital of France."
    query_params = QueryParameters(
        format="html",
        search="local",
        engine=Engine.GRAPHRAG,
        context_params=ContextParameters(query="What is the capital of France?", project_dir=Path("."), context_size=100),
        system_prompt_additional=instruction,
    )
    context_params = inject_system_prompt_to_query_params(query_params)
    assert instruction in context_params.query
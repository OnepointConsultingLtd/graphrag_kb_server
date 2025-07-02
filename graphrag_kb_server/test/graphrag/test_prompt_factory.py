from pathlib import Path

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.rag_parameters import QueryParameters, ContextParameters
from graphrag_kb_server.service.graphrag.prompt_factory import (
    inject_system_prompt_to_query_params,
    create_conversation_history,
)


def test_inject_system_prompt_to_query_params():
    instruction = "You are a helpful assistant that can answer questions about the capital of France."
    query_params = QueryParameters(
        format="html",
        search="local",
        engine=Engine.GRAPHRAG,
        context_params=ContextParameters(
            query="What is the capital of France?",
            project_dir=Path("."),
            context_size=100,
        ),
        system_prompt_additional=instruction,
    )
    context_params = inject_system_prompt_to_query_params(query_params)
    assert instruction in context_params.query


def test_create_conversation_history():
    query_params = QueryParameters(
        format="json",
        search="local",
        engine=Engine.GRAPHRAG,
        context_params=ContextParameters(
            query="What is the capital of France?",
            project_dir=Path("test"),
            context_size=1000,
        ),
        chat_history=[
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
        ],
    )
    conversation_history = create_conversation_history(query_params)
    assert conversation_history is not None
    assert len(conversation_history.turns) == 2
    for turn in conversation_history.turns:
        print(turn)


def test_create_conversation_history_empty():
    query_params = QueryParameters(
        format="json",
        search="local",
        engine=Engine.GRAPHRAG,
        context_params=ContextParameters(
            query="What is the capital of France?",
            project_dir=Path("test"),
            context_size=1000,
        ),
    )
    conversation_history = create_conversation_history(query_params)
    assert conversation_history is None

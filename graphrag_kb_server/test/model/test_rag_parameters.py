from pathlib import Path

from graphrag_kb_server.model.rag_parameters import (
    QueryParameters,
    convert_to_lightrag_query_params,
    MessageType,
    ContextParameters,
)
from graphrag_kb_server.model.web_format import Format
from graphrag_kb_server.model.engines import Engine


def test_convert_to_lightrag_query_params():
    hl_keywords = ["Artificial Intelligence", "Automation"]
    ll_keywords = ["Machine Learning", "Robotics"]
    query_params = QueryParameters(
        format=Format.HTML.value,
        engine=Engine.LIGHTRAG,
        search="local",
        context_params=ContextParameters(
            query="What is the capital of France?",
            project_dir=Path("test_project"),
            context_size=100,
        ),
        hl_keywords=hl_keywords,
        ll_keywords=ll_keywords,
        chat_history=[
            {"role": MessageType.USER.value, "content": "How are you today?"},
            {"role": MessageType.ASSISTANT.value, "content": "I am fine, thank you!"},
        ],
    )
    param = convert_to_lightrag_query_params(query_params)
    assert param.mode == "local"
    assert param.hl_keywords == hl_keywords
    assert param.ll_keywords == ll_keywords
    assert param.conversation_history == [
        {"role": "user", "content": "How are you today?"},
        {"role": "assistant", "content": "I am fine, thank you!"},
    ]

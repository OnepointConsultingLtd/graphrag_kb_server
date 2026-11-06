import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.model.websocket_commands import Command
from graphrag_kb_server.service import trendiness_research
from graphrag_kb_server.service.project_config_service import ProjectConfig

MODULE = "graphrag_kb_server.service.trendiness_research"
TREND_JSON = json.dumps(
    {
        "main_topics": ["AI"],
        "trend_class": "HOT",
        "confidence": 0.9,
        "reasoning": "r",
        "recent_findings": "f",
        "visited_urls": [],
    }
)


def make_config(**overrides) -> ProjectConfig:
    return replace(ProjectConfig.from_env(), project_label="tenant/project", **overrides)


class FakeOpenRouter:
    created: list["FakeOpenRouter"] = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.send_async = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=TREND_JSON))]
            )
        )
        self.chat = SimpleNamespace(send_async=self.send_async)
        FakeOpenRouter.created.append(self)


@pytest.fixture(autouse=True)
def fake_openrouter(monkeypatch):
    FakeOpenRouter.created = []
    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouter)


@pytest.mark.asyncio
async def test_uses_key_and_model_of_the_project():
    config = make_config(openrouter_api_key="or-project", openrouter_model="model-project")
    result = await trendiness_research.assess_document_trendiness("text", config)
    assert result.main_topics == ["AI"]
    client = FakeOpenRouter.created[0]
    assert client.api_key == "or-project"
    assert client.send_async.call_args.kwargs["model"] == "model-project"


@pytest.mark.asyncio
async def test_explicit_key_and_model_win_over_the_config():
    """Regression: the explicit key used to be validated but then ignored."""
    config = make_config(openrouter_api_key="or-project", openrouter_model="model-project")
    await trendiness_research.assess_document_trendiness(
        "text", config, model="explicit-model", api_key="explicit-key"
    )
    client = FakeOpenRouter.created[0]
    assert client.api_key == "explicit-key"
    assert client.send_async.call_args.kwargs["model"] == "explicit-model"


@pytest.mark.asyncio
async def test_missing_key_raises():
    config = make_config(openrouter_api_key="")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        await trendiness_research.assess_document_trendiness("text", config)
    assert FakeOpenRouter.created == []


@pytest.mark.asyncio
async def test_processor_task_assesses_with_the_config_of_the_project(monkeypatch):
    project_dir = Path("/root/tenant/lightrag/project")
    config = make_config(openrouter_api_key="or-project")
    trend_result = trendiness_research.TrendResult(**json.loads(TREND_JSON))
    lookup = AsyncMock(return_value=config)
    assess = AsyncMock(return_value=trend_result)
    send_message = AsyncMock()
    monkeypatch.setattr(f"{MODULE}.find_project_dir", AsyncMock(return_value=project_dir))
    monkeypatch.setattr(f"{MODULE}.get_project_id_from_path", AsyncMock(return_value=1))
    monkeypatch.setattr(f"{MODULE}.get_document_trend_result_by_path", AsyncMock(return_value=None))
    monkeypatch.setattr(f"{MODULE}.insert_document_trend_result", AsyncMock())
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", lookup)
    monkeypatch.setattr(f"{MODULE}.assess_document_trendiness", assess)

    await trendiness_research.document_trendiness_processor_task(
        "token", "project", "doc-1", send_message=send_message, content="some text"
    )

    lookup.assert_awaited_once_with(project_dir)
    assess.assert_awaited_once_with("some text", config)
    assert send_message.call_args.args[0] == Command.DOCUMENT_TRENDINESS_END

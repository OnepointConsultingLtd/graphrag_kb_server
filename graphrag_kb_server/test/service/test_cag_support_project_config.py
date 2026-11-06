from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.service.cag import cag_support
from graphrag_kb_server.service.project_config_service import (
    ProjectConfig,
    invalidate_project_runtime_caches,
)

MODULE = "graphrag_kb_server.service.cag.cag_support"
TOPICS_JSON = '{"topics": [{"name": "AI", "description": "d", "type": "category"}]}'


def make_config(**overrides) -> ProjectConfig:
    return replace(ProjectConfig.from_env(), project_label="tenant/project", **overrides)


class FakeGeminiClient:
    """Records the key it was created with and the models it is used with."""

    created: list["FakeGeminiClient"] = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.cache_models: list[str] = []
        self.chat_models: list[str] = []
        self.generate_models: list[str] = []
        self.aio = SimpleNamespace(
            caches=SimpleNamespace(get=self._get_cache, create=self._create_cache),
            chats=SimpleNamespace(create=self._create_chat),
            models=SimpleNamespace(generate_content=self._generate_content),
        )
        FakeGeminiClient.created.append(self)

    async def _get_cache(self, name):
        raise RuntimeError("no such cache")

    async def _create_cache(self, model, config):
        self.cache_models.append(model)
        return SimpleNamespace(
            name="cachedContents/1",
            display_name="cache",
            usage_metadata=SimpleNamespace(total_token_count=1),
        )

    def _create_chat(self, model, config):
        self.chat_models.append(model)
        return SimpleNamespace(client=self)

    async def _generate_content(self, model, contents, config):
        self.generate_models.append(model)
        return SimpleNamespace(text=TOPICS_JSON)


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch) -> Path:
    """A project directory with a document, in the <root>/<schema>/<engine>/<project> layout."""
    directory = tmp_path / "tenant" / "cag" / "project"
    directory.mkdir(parents=True)
    (directory / "doc.txt").write_text("some document", encoding="utf-8")
    FakeGeminiClient.created = []
    monkeypatch.setattr(f"{MODULE}.genai.Client", FakeGeminiClient)
    yield directory
    cag_support.invalidate_chat_cache(directory)
    cag_support.TOPICS_CACHE.clear(directory)


@pytest.mark.asyncio
async def test_chat_uses_key_and_model_of_the_project(project_dir, monkeypatch):
    config = make_config(gemini_api_key="gemini-p", cag_model="cag-model-p")
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", AsyncMock(return_value=config))

    await cag_support.acreate_cag(project_dir, "conversation-2")

    client = FakeGeminiClient.created[0]
    assert client.api_key == "gemini-p"
    assert client.cache_models == ["cag-model-p"]
    assert client.chat_models == ["cag-model-p"]


@pytest.mark.asyncio
async def test_cached_chat_does_not_resolve_the_config_again(project_dir, monkeypatch):
    lookup = AsyncMock(return_value=make_config(gemini_api_key="g", cag_model="m"))
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", lookup)

    first = await cag_support.acreate_cag(project_dir, "conversation-2")
    second = await cag_support.acreate_cag(project_dir, "conversation-2")

    assert first is second
    assert lookup.await_count == 1


@pytest.mark.asyncio
async def test_changed_settings_are_used_after_invalidation(project_dir, monkeypatch):
    lookup = AsyncMock(
        side_effect=[
            make_config(gemini_api_key="key-1", cag_model="model-1"),
            make_config(gemini_api_key="key-2", cag_model="model-2"),
        ]
    )
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", lookup)

    await cag_support.acreate_cag(project_dir, "conversation-2")
    invalidate_project_runtime_caches(project_dir)
    await cag_support.acreate_cag(project_dir, "conversation-2")

    first, second = FakeGeminiClient.created
    assert (first.api_key, first.chat_models) == ("key-1", ["model-1"])
    assert (second.api_key, second.chat_models) == ("key-2", ["model-2"])


@pytest.mark.asyncio
async def test_main_topics_use_key_and_model_of_the_project(project_dir, monkeypatch):
    config = make_config(gemini_api_key="gemini-t", cag_model="cag-topics-model")
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", AsyncMock(return_value=config))

    topics = await cag_support.extract_main_topics(project_dir)

    assert [topic.name for topic in topics.topics] == ["AI"]
    client = FakeGeminiClient.created[0]
    assert client.api_key == "gemini-t"
    assert client.generate_models == ["cag-topics-model"]


@pytest.mark.asyncio
async def test_cached_topics_do_not_resolve_the_config(project_dir, monkeypatch):
    lookup = AsyncMock(return_value=make_config(gemini_api_key="g", cag_model="m"))
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", lookup)

    await cag_support.extract_main_topics(project_dir)
    await cag_support.extract_main_topics(project_dir)

    assert lookup.await_count == 1

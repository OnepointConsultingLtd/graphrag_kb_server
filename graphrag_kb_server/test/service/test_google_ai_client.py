from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from graphrag_kb_server.service import google_ai_client
from graphrag_kb_server.service.project_config_service import ProjectConfig

MODULE = "graphrag_kb_server.service.google_ai_client"


class Answer(BaseModel):
    value: str


def make_config(**overrides) -> ProjectConfig:
    """The .env configuration with some values replaced, like a project with overrides."""
    return replace(ProjectConfig.from_env(), project_label="tenant/project", **overrides)


class FakeGeminiClient:
    created: list["FakeGeminiClient"] = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.models_used: list[str] = []
        self.aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=self._generate_content)
        )
        FakeGeminiClient.created.append(self)

    async def _generate_content(self, model, contents, config):
        self.models_used.append(model)
        return SimpleNamespace(text='{"value": "from-gemini"}')


class FakeAsyncOpenAI:
    created: list["FakeAsyncOpenAI"] = []

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.parse = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"value": "from-openai"}')
                    )
                ]
            )
        )
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(parse=self.parse))
        )
        FakeAsyncOpenAI.created.append(self)


class FakeOpenRouter:
    created: list["FakeOpenRouter"] = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.send_async = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"value": "from-openrouter"}')
                    )
                ]
            )
        )
        self.chat = SimpleNamespace(send_async=self.send_async)
        FakeOpenRouter.created.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def fake_clients(monkeypatch):
    for fake in (FakeGeminiClient, FakeAsyncOpenAI, FakeOpenRouter):
        fake.created = []
    monkeypatch.setattr(f"{MODULE}.genai.Client", FakeGeminiClient)
    monkeypatch.setattr(f"{MODULE}.AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouter)


@pytest.mark.asyncio
@pytest.mark.parametrize("key, model", [("gemini-a", "gemini-model-a"), ("gemini-b", "gemini-model-b")])
async def test_gemini_uses_key_and_default_model_of_the_project(key, model):
    config = make_config(gemini_api_key=key, lightrag_model=model)
    result = await google_ai_client.structured_completion("sys", "user", Answer, config=config)
    assert result == {"value": "from-gemini"}
    client = FakeGeminiClient.created[0]
    assert client.api_key == key
    assert client.models_used == [model]


@pytest.mark.asyncio
async def test_openai_uses_key_of_the_project():
    config = make_config(openai_api_key="openai-p", lightrag_model="gpt-4o")
    result = await google_ai_client.structured_completion("sys", "user", Answer, config=config)
    assert result == {"value": "from-openai"}
    client = FakeAsyncOpenAI.created[0]
    assert client.api_key == "openai-p"
    assert client.parse.call_args.kwargs["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_openai_without_key_falls_back_to_sdk_lookup():
    config = make_config(openai_api_key="", lightrag_model="gpt-4o")
    await google_ai_client.structured_completion("sys", "user", Answer, config=config)
    assert FakeAsyncOpenAI.created[0].api_key is None


@pytest.mark.asyncio
async def test_openrouter_uses_key_provider_and_model_of_the_project():
    config = make_config(
        openrouter_api_key="or-p",
        openrouter_provider="provider-p",
        lightrag_model="google/some-model",
    )
    result = await google_ai_client.structured_completion("sys", "user", Answer, config=config)
    assert result == {"value": "from-openrouter"}
    client = FakeOpenRouter.created[0]
    assert client.api_key == "or-p"
    sent = client.send_async.call_args.kwargs
    assert sent["model"] == "google/some-model"
    assert sent["provider"] == {"name": "provider-p"}


@pytest.mark.asyncio
async def test_openrouter_without_provider_sends_none():
    config = make_config(openrouter_provider=None, lightrag_model="google/some-model")
    await google_ai_client.structured_completion("sys", "user", Answer, config=config)
    assert "provider" not in FakeOpenRouter.created[0].send_async.call_args.kwargs


@pytest.mark.asyncio
async def test_explicit_model_overrides_the_project_default():
    config = make_config(lightrag_model="gemini-default", gemini_api_key="g")
    await google_ai_client.structured_completion(
        "sys", "user", Answer, config=config, model="gemini-explicit"
    )
    assert FakeGeminiClient.created[0].models_used == ["gemini-explicit"]


@pytest.mark.asyncio
async def test_two_projects_use_their_own_keys():
    first = make_config(gemini_api_key="key-1", lightrag_model="gemini-x")
    second = make_config(gemini_api_key="key-2", lightrag_model="gemini-x")
    await google_ai_client.structured_completion("s", "u", Answer, config=first)
    await google_ai_client.structured_completion("s", "u", Answer, config=second)
    assert [client.api_key for client in FakeGeminiClient.created] == ["key-1", "key-2"]


def test_default_model_is_not_frozen_at_import_time():
    """The model comes from the config of each call, not from a default evaluated at import."""
    import inspect

    parameter = inspect.signature(google_ai_client.structured_completion).parameters["model"]
    assert parameter.default is None

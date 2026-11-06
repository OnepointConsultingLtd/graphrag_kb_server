import inspect
from dataclasses import replace
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.config import LightRAGModelType
from graphrag_kb_server.service.lightrag import lightrag_model_support as support
from graphrag_kb_server.service.project_config_service import ProjectConfig

MODULE = "graphrag_kb_server.service.lightrag.lightrag_model_support"


def make_config(**overrides) -> ProjectConfig:
    """The .env configuration with some values replaced, like a project with overrides."""
    return replace(ProjectConfig.from_env(), project_label="tenant/project", **overrides)


CONFIG_A = make_config(
    gemini_api_key="gemini-a",
    openai_api_key="openai-a",
    openrouter_api_key="openrouter-a",
    openrouter_provider="provider-a",
    togetherai_api_key="together-a",
    lightrag_model="model-a",
)
CONFIG_B = make_config(
    gemini_api_key="gemini-b",
    openai_api_key="openai-b",
    openrouter_api_key="openrouter-b",
    openrouter_provider="provider-b",
    togetherai_api_key="together-b",
    lightrag_model="model-b",
)


class FakeGeminiClient:
    """Records the key and the model it is used with."""

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
        return SimpleNamespace(text="answer", usage_metadata=None)


@pytest.fixture(autouse=True)
def reset_fake_clients():
    FakeGeminiClient.created = []


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [CONFIG_A, CONFIG_B])
async def test_gemini_model_func_uses_key_and_model_of_the_project(monkeypatch, config):
    monkeypatch.setattr(f"{MODULE}.genai.Client", FakeGeminiClient)
    answer = await support.gemini_model_func("question", config=config)
    assert answer == "answer"
    client = FakeGeminiClient.created[0]
    assert client.api_key == config.gemini_api_key
    assert client.models_used == [config.lightrag_model]


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [CONFIG_A, CONFIG_B])
async def test_openai_model_func_uses_key_of_the_project(monkeypatch, config):
    structured = AsyncMock(return_value="answer")
    monkeypatch.setattr(f"{MODULE}.structured_completion", structured)
    await support.openai_model_func("question", config=config)
    client = structured.call_args.args[0]
    assert client.api_key == config.openai_api_key
    assert structured.call_args.kwargs["config"] is config


@pytest.mark.asyncio
async def test_openai_model_func_without_key_falls_back_to_sdk_lookup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-process-environment")
    structured = AsyncMock(return_value="answer")
    monkeypatch.setattr(f"{MODULE}.structured_completion", structured)
    await support.openai_model_func("question", config=make_config(openai_api_key=""))
    assert structured.call_args.args[0].api_key == "from-process-environment"


@pytest.mark.asyncio
async def test_togetherai_model_func_uses_key_of_the_project(monkeypatch):
    created_keys = []

    class FakeTogether:
        def __init__(self, api_key):
            created_keys.append(api_key)

    monkeypatch.setattr(f"{MODULE}.AsyncTogether", FakeTogether)
    monkeypatch.setattr(f"{MODULE}.structured_completion", AsyncMock())
    await support.togetherai_model_func("q", config=CONFIG_A)
    await support.togetherai_model_func("q", config=CONFIG_B)
    assert created_keys == ["together-a", "together-b"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_openrouter_model_func_uses_key_of_the_project(monkeypatch, stream):
    created_keys = []

    class FakeOpenRouter:
        def __init__(self, api_key):
            created_keys.append(api_key)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouter)
    structured = AsyncMock(return_value="answer")
    monkeypatch.setattr(f"{MODULE}.structured_completion", structured)
    await support.openrouter_model_func("q", config=CONFIG_B, stream=stream)
    assert created_keys == ["openrouter-b"]
    assert structured.call_args.kwargs["config"] is CONFIG_B


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [CONFIG_A, CONFIG_B])
async def test_structured_completion_uses_model_and_provider_of_the_project(
    monkeypatch, config
):
    class FakeOpenRouter:
        def __init__(self):
            self.chat = SimpleNamespace(send_async=AsyncMock(return_value=_response()))

    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouter)
    client = FakeOpenRouter()
    await support.structured_completion(client, "prompt", "system", config=config)
    sent = client.chat.send_async.call_args.kwargs
    assert sent["model"] == config.lightrag_model
    assert sent["provider"] == {"name": config.openrouter_provider}


@pytest.mark.asyncio
async def test_structured_completion_without_provider_sends_none(monkeypatch):
    class FakeOpenRouter:
        def __init__(self):
            self.chat = SimpleNamespace(send_async=AsyncMock(return_value=_response()))

    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouter)
    client = FakeOpenRouter()
    config = make_config(openrouter_provider=None, lightrag_model="m")
    await support.structured_completion(client, "prompt", config=config)
    assert "provider" not in client.chat.send_async.call_args.kwargs


def _response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="text"))], usage=None
    )


@pytest.mark.parametrize(
    "model_type, model, expected_function",
    [
        (LightRAGModelType.GOOGLE, "gemini-x", support.gemini_model_func),
        (LightRAGModelType.OPENAI, "gpt-4o", support.openai_model_func),
        (LightRAGModelType.OPENAI, "gpt-4o-mini", support.openai_model_func),
        (LightRAGModelType.TOGETHERAI, "any", support.togetherai_model_func),
        (LightRAGModelType.OPENROUTER, "any/model", support.openrouter_model_func),
    ],
)
def test_select_model_func_binds_the_project_config(model_type, model, expected_function):
    config = make_config(lightrag_model_type=model_type.value, lightrag_model=model)
    selected = support.select_model_func(config)
    assert isinstance(selected, partial)
    assert selected.func is expected_function
    assert selected.keywords == {"config": config}
    assert inspect.iscoroutinefunction(selected)


def test_select_model_func_rejects_unsupported_openai_model():
    config = make_config(lightrag_model_type="openai", lightrag_model="claude-x")
    with pytest.raises(ValueError, match="Unsupported OpenAI"):
        support.select_model_func(config)


def test_select_model_func_rejects_invalid_model_type():
    with pytest.raises(ValueError, match="Invalid LightRAG model type"):
        support.select_model_func(make_config(lightrag_model_type="bogus"))


@pytest.mark.asyncio
async def test_openai_model_func_factory_uses_key_of_the_project(monkeypatch):
    complete = AsyncMock(return_value="answer")
    monkeypatch.setattr(f"{MODULE}.openai_complete_if_cache", complete)
    model_func = support.openai_model_func_factory("gpt-4o", CONFIG_A)
    await model_func("question")
    assert complete.call_args.kwargs["api_key"] == "openai-a"


# --- OpenRouter request compatibility (reasoning effort, strict schema, errors) -----------


class FakeOpenRouterClient:
    """An OpenRouter client whose ``chat.send_async`` is an AsyncMock."""

    def __init__(self, send_async: AsyncMock):
        self.chat = SimpleNamespace(send_async=send_async)


@pytest.fixture
def fake_openrouter(monkeypatch):
    """Make the fake client pass the ``isinstance(client, OpenRouter)`` check."""
    monkeypatch.setattr(f"{MODULE}.OpenRouter", FakeOpenRouterClient)


def _structured_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"a": 1}'))],
        usage=None,
    )


async def _send_structured(config: ProjectConfig) -> dict:
    """Run a structured LLMSearchResults completion and return the request sent."""
    from graphrag_kb_server.model.search.search import LLMSearchResults

    client = FakeOpenRouterClient(AsyncMock(return_value=_structured_response()))
    await support.structured_completion(
        client,
        "prompt",
        "system",
        config=config,
        structured_output=True,
        structured_output_format=LLMSearchResults,
    )
    return client.chat.send_async.call_args.kwargs


def _all_object_schemas(schema: dict) -> list[dict]:
    """Every object schema in a JSON schema, including the ones in $defs and nested ones."""
    found = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append(schema)
        for value in schema.values():
            found.extend(_all_object_schemas(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_all_object_schemas(item))
    return found


@pytest.mark.parametrize("effort", ["minimal", "none", "low"])
def test_build_reasoning_param_returns_configured_effort(effort):
    config = make_config(lightrag_reasoning_effort=effort)
    assert support._build_reasoning_param(config) == {"effort": effort}


@pytest.mark.parametrize("effort", ["", "  ", None])
def test_build_reasoning_param_returns_none_without_effort(effort):
    config = make_config(lightrag_reasoning_effort=effort)
    assert support._build_reasoning_param(config) is None


@pytest.mark.asyncio
async def test_structured_completion_sends_configured_reasoning(fake_openrouter):
    config = make_config(lightrag_model="m", lightrag_reasoning_effort="none")
    client = FakeOpenRouterClient(AsyncMock(return_value=_response()))
    await support.structured_completion(client, "prompt", config=config)
    assert client.chat.send_async.call_args.kwargs["reasoning"] == {"effort": "none"}


@pytest.mark.asyncio
async def test_structured_completion_omits_reasoning_without_effort(fake_openrouter):
    config = make_config(lightrag_model="m", lightrag_reasoning_effort="")
    client = FakeOpenRouterClient(AsyncMock(return_value=_response()))
    await support.structured_completion(client, "prompt", config=config)
    assert "reasoning" not in client.chat.send_async.call_args.kwargs


@pytest.mark.parametrize(
    "model_name, expected",
    [
        ("openai/gpt-6.1-terra", True),
        ("OpenAI/gpt-4o", True),
        ("gpt-4o-mini", True),
        ("o3-mini", True),
        ("o4-mini", True),
        ("google/gemini-3-flash-preview", False),
        ("anthropic/claude-sonnet-4.5", False),
        ("claude-sonnet-4.5", False),
        ("openrouter/auto", False),
    ],
)
def test_is_openai_model(model_name, expected):
    assert support._is_openai_model(model_name) is expected


@pytest.mark.asyncio
async def test_openai_model_on_openrouter_gets_strict_compatible_schema(fake_openrouter):
    sent = await _send_structured(make_config(lightrag_model="openai/gpt-6.1-terra"))
    json_schema = sent["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    assert json_schema["name"] == "LLMSearchResults"
    object_schemas = _all_object_schemas(json_schema["schema"])
    # The root schema and the LLMSearchDocument definition at least.
    assert len(object_schemas) >= 2
    for object_schema in object_schemas:
        assert object_schema["additionalProperties"] is False
        assert set(object_schema["required"]) == set(object_schema["properties"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_name", ["google/gemini-3-flash-preview", "anthropic/claude-sonnet-4.5"]
)
async def test_non_openai_model_on_openrouter_keeps_pydantic_schema(
    fake_openrouter, model_name
):
    from graphrag_kb_server.model.search.search import LLMSearchResults

    sent = await _send_structured(make_config(lightrag_model=model_name))
    json_schema = sent["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    assert json_schema["schema"] == LLMSearchResults.model_json_schema()


@pytest.mark.asyncio
async def test_direct_openai_client_sends_no_strict_flag():
    from openai import AsyncOpenAI

    from graphrag_kb_server.model.search.search import LLMSearchResults

    client = AsyncOpenAI(api_key="test-key")
    create = AsyncMock(return_value=_structured_response())
    client.chat.completions.create = create
    await support.structured_completion(
        client,
        "prompt",
        config=make_config(lightrag_model="gpt-4o"),
        structured_output=True,
        structured_output_format=LLMSearchResults,
    )
    sent = create.call_args.kwargs
    assert "reasoning" not in sent
    assert "strict" not in sent["response_format"]["json_schema"]
    assert sent["response_format"]["json_schema"]["schema"] == (
        LLMSearchResults.model_json_schema()
    )


@pytest.mark.asyncio
async def test_openrouter_error_body_is_logged_and_reraised(fake_openrouter, monkeypatch):
    import httpx
    from openrouter.errors import OpenRouterError

    error_body = (
        '{"error": {"message": "Provider returned error", "metadata": '
        '{"raw": "Unsupported value: \'minimal\'", "provider_name": "OpenAI"}}}'
    )
    raw_response = httpx.Response(
        400, text=error_body, request=httpx.Request("POST", "https://openrouter.ai")
    )
    error = OpenRouterError("Provider returned error", raw_response)
    logged_errors = []
    monkeypatch.setattr(f"{MODULE}.logger.error", logged_errors.append)

    client = FakeOpenRouterClient(AsyncMock(side_effect=error))
    config = make_config(lightrag_model="openai/gpt-6.1-terra")
    with pytest.raises(OpenRouterError) as raised:
        await support.structured_completion(client, "prompt", config=config)

    assert raised.value is error
    assert len(logged_errors) == 1
    assert "400" in logged_errors[0]
    assert "openai/gpt-6.1-terra" in logged_errors[0]
    assert "Unsupported value: 'minimal'" in logged_errors[0]

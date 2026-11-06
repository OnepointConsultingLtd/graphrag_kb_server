from dataclasses import replace
from unittest.mock import AsyncMock

import numpy as np
import pytest
from lightrag.llm.openai import openai_embed

from graphrag_kb_server.service.lightrag import lightrag_embedding as embedding
from graphrag_kb_server.service.project_config_service import ProjectConfig


def make_config(**overrides) -> ProjectConfig:
    return replace(ProjectConfig.from_env(), **overrides)


def test_default_model_matches_what_lightrag_used_before():
    """Projects which do not configure anything keep the embeddings they were indexed with."""
    assert embedding.DEFAULT_EMBEDDING_MODEL == openai_embed.model_name
    assert (
        embedding.get_embedding_dimension(embedding.DEFAULT_EMBEDDING_MODEL)
        == openai_embed.embedding_dim
    )
    assert embedding.EMBEDDING_MAX_TOKEN_SIZE == openai_embed.max_token_size


@pytest.mark.parametrize(
    "model, dimension",
    [
        ("text-embedding-3-small", 1536),
        ("text-embedding-3-large", 3072),
        ("text-embedding-ada-002", 1536),
    ],
)
def test_known_models_have_their_dimension(model, dimension):
    assert embedding.get_embedding_dimension(model) == dimension


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError, match="Unsupported embedding model 'nope'"):
        embedding.get_embedding_dimension("nope")


def test_build_embedding_func_sets_dimension_and_model_name():
    func = embedding.build_embedding_func(
        make_config(openai_api_model_embedding="text-embedding-3-large")
    )
    assert func.embedding_dim == 3072
    assert func.model_name == "text-embedding-3-large"
    assert func.max_token_size == 8192


def test_build_embedding_func_falls_back_to_default_model_when_not_configured():
    func = embedding.build_embedding_func(make_config(openai_api_model_embedding=None))
    assert func.model_name == embedding.DEFAULT_EMBEDDING_MODEL
    assert func.embedding_dim == 1536


def test_build_embedding_func_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unsupported embedding model"):
        embedding.build_embedding_func(make_config(openai_api_model_embedding="nope"))


@pytest.mark.asyncio
@pytest.mark.parametrize("api_key, expected_key", [("sk-project", "sk-project"), ("", None)])
async def test_embedding_calls_openai_with_model_and_key_of_the_project(
    monkeypatch, api_key, expected_key
):
    fake_embed = AsyncMock(return_value=np.zeros((1, 3072)))
    monkeypatch.setattr(embedding.openai_embed, "func", fake_embed)
    func = embedding.build_embedding_func(
        make_config(
            openai_api_key=api_key, openai_api_model_embedding="text-embedding-3-large"
        )
    )
    await func(["some text"])
    assert fake_embed.call_args.kwargs["model"] == "text-embedding-3-large"
    assert fake_embed.call_args.kwargs["api_key"] == expected_key

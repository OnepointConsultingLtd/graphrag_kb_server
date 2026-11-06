from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.service.lightrag import lightrag_init
from graphrag_kb_server.service.project_config_service import (
    ProjectConfig,
    invalidate_project_runtime_caches,
)

MODULE = "graphrag_kb_server.service.lightrag.lightrag_init"


class FakeLightRAG:
    """Stands in for LightRAG: records how it was built and skips the storage setup."""

    created: list["FakeLightRAG"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.llm_response_cache = SimpleNamespace(global_config={})
        FakeLightRAG.created.append(self)

    async def initialize_storages(self):
        pass


def project_dir(root: Path, name: str) -> Path:
    path = root / "tenant" / "lightrag" / name
    path.mkdir(parents=True)
    return path


@pytest.fixture
def fake_environment(monkeypatch):
    """Replaces LightRAG and the project configuration lookup (one config per project name)."""
    FakeLightRAG.created = []
    configs = {
        "p1": replace(
            ProjectConfig.from_env(),
            gemini_api_key="gemini-p1",
            lightrag_model_type="google",
            lightrag_model="model-p1",
            openai_api_model_embedding="text-embedding-3-small",
        ),
        "p2": replace(
            ProjectConfig.from_env(),
            openai_api_key="openai-p2",
            lightrag_model_type="openai",
            lightrag_model="gpt-4o",
            openai_api_model_embedding="text-embedding-3-large",
        ),
    }

    async def config_for_dir(folder: Path) -> ProjectConfig:
        return configs[folder.name]

    monkeypatch.setattr(f"{MODULE}.LightRAG", FakeLightRAG)
    monkeypatch.setattr(f"{MODULE}.get_project_config_for_dir", config_for_dir)
    monkeypatch.setattr(f"{MODULE}.initialize_storages", AsyncMock())
    monkeypatch.setattr(f"{MODULE}.initialize_pipeline_status", AsyncMock())
    return configs


@pytest.mark.asyncio
async def test_each_project_gets_its_own_model_and_embedding_function(
    tmp_path, fake_environment
):
    first_dir = project_dir(tmp_path, "p1")
    second_dir = project_dir(tmp_path, "p2")
    try:
        await lightrag_init.initialize_rag(first_dir)
        await lightrag_init.initialize_rag(second_dir)
        first, second = FakeLightRAG.created

        assert isinstance(first.kwargs["llm_model_func"], partial)
        assert first.kwargs["llm_model_func"].keywords["config"].gemini_api_key == "gemini-p1"
        assert first.kwargs["embedding_func"].model_name == "text-embedding-3-small"
        assert first.kwargs["embedding_func"].embedding_dim == 1536

        assert second.kwargs["llm_model_func"].keywords["config"].openai_api_key == "openai-p2"
        assert second.kwargs["embedding_func"].model_name == "text-embedding-3-large"
        assert second.kwargs["embedding_func"].embedding_dim == 3072
    finally:
        lightrag_init.lightrag_cache.clear(first_dir)
        lightrag_init.lightrag_cache.clear(second_dir)


@pytest.mark.asyncio
async def test_instance_is_cached_until_the_runtime_caches_are_invalidated(
    tmp_path, fake_environment
):
    folder = project_dir(tmp_path, "p1")
    try:
        first = await lightrag_init.initialize_rag(folder)
        assert await lightrag_init.initialize_rag(folder) is first
        assert len(FakeLightRAG.created) == 1

        invalidate_project_runtime_caches(folder)

        rebuilt = await lightrag_init.initialize_rag(folder)
        assert rebuilt is not first
        assert len(FakeLightRAG.created) == 2
    finally:
        lightrag_init.lightrag_cache.clear(folder)


@pytest.mark.asyncio
async def test_changed_settings_are_used_after_invalidation(tmp_path, fake_environment):
    folder = project_dir(tmp_path, "p1")
    try:
        await lightrag_init.initialize_rag(folder)
        fake_environment["p1"] = replace(
            fake_environment["p1"], gemini_api_key="gemini-changed"
        )
        invalidate_project_runtime_caches(folder)
        rag = await lightrag_init.initialize_rag(folder)
        assert rag.kwargs["llm_model_func"].keywords["config"].gemini_api_key == "gemini-changed"
    finally:
        lightrag_init.lightrag_cache.clear(folder)

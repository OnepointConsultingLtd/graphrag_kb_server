from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from graphrag_kb_server.model.search.entity import Entity
from graphrag_kb_server.model.search.match_query import MatchOutput, MatchQuery
from graphrag_kb_server.service.project_config_service import ProjectConfig
from graphrag_kb_server.service.search import matching

PROJECT_DIR = Path("/root/tenant/lightrag/project")
CONFIG = replace(
    ProjectConfig.from_env(), lightrag_model="project-model", project_label="tenant/project"
)
QUERY = MatchQuery(
    question="How can I automate?",
    user_profile="engineer",
    topics_of_interest=(Entity(name="AI", description="Artificial intelligence"),),
)
EXISTING_ENTITIES = [Entity(name="Automation", description="Process automation")]


@pytest.mark.asyncio
async def test_match_entities_uses_the_config_of_the_project(monkeypatch):
    completion = AsyncMock(
        return_value={
            "entities": [
                {"entity": "Automation", "score": 0.9, "abstraction": "high-level"}
            ]
        }
    )
    monkeypatch.setattr(matching, "structured_completion", completion)

    result = await matching.match_entities(QUERY, EXISTING_ENTITIES, CONFIG)

    assert completion.call_args.kwargs["config"] is CONFIG
    # The model is not passed explicitly any more: it defaults to the model of the config.
    assert "model" not in completion.call_args.kwargs
    assert [entity.entity for entity in result.entities] == ["Automation"]


@pytest.mark.asyncio
async def test_match_entities_with_lightrag_resolves_config_of_the_project(monkeypatch):
    config_lookup = AsyncMock(return_value=CONFIG)
    match_entities = AsyncMock(return_value=matching.EntityList(entities=[]))
    monkeypatch.setattr(matching, "get_expanded_entities", AsyncMock(return_value=None))
    monkeypatch.setattr(
        matching,
        "get_top_centrality_scores_by_type_as_pd",
        AsyncMock(return_value=pd.DataFrame()),
    )
    monkeypatch.setattr(matching, "_convert_df_to_entities", lambda df: EXISTING_ENTITIES)
    monkeypatch.setattr(matching, "insert_expanded_entities", AsyncMock())
    monkeypatch.setattr(matching, "get_project_config_for_dir", config_lookup)
    monkeypatch.setattr(matching, "match_entities", match_entities)

    output = await matching.match_entities_with_lightrag(PROJECT_DIR, QUERY)

    assert isinstance(output, MatchOutput)
    config_lookup.assert_awaited_once_with(PROJECT_DIR)
    assert match_entities.call_args.args == (QUERY, EXISTING_ENTITIES, CONFIG)

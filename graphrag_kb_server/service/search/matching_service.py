import asyncio
import json
from pathlib import Path
from collections import defaultdict

import pandas as pd
from google import genai
from google.genai import types

from graphrag_kb_server.model.search.match_query import MatchQuery, MatchOutput
from graphrag_kb_server.model.search.entity import Entity, EntityList, EntityWithScore
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.config import cfg, lightrag_cfg


def _convert_df_to_entities(df: pd.DataFrame) -> list[Entity]:
    return [
        Entity(name=e[0], type=e[1], description=e[2])
        for e in zip(df["entity_id"], df["entity_type"], df["description"])
    ]


async def match_entities_with_lightrag(
    project_dir: Path, query: MatchQuery
) -> MatchOutput:
    user_profile, topics_of_interest, entity_types, entities_limit = (
        query.user_profile,
        query.topics_of_interest,
        query.entity_types,
        query.entities_limit,
    )
    df = await asyncio.to_thread(get_sorted_centrality_scores_as_pd, project_dir)
    df = df[df["entity_type"].isin(entity_types)][:entities_limit]
    all_entities = _convert_df_to_entities(df)
    entity_list = await match_entities(user_profile, topics_of_interest, all_entities)
    entity_list = [entity for entity in entity_list.entities if entity.score > 0]
    entity_dict = defaultdict(list)
    entity_type_dict = {e.name: e.type for e in all_entities}
    for entity in entity_list:
        if entity.entity in entity_type_dict:
            entity_dict[entity_type_dict[entity.entity]].append(entity)
    entity_dict = {e[0]: EntityList(entities=e[1]) for e in entity_dict.items()}
    return MatchOutput(entity_dict=entity_dict)


def _convert_entities_to_str(entities: list[Entity]) -> str:
    return "\n".join(
        [f"- {entity.name}\n{entity.description[:150]}" for entity in entities]
    )


async def match_entities(
    user_profile: str, topics_of_interest: list[Entity], existing_entities: list[Entity]
) -> EntityList:
    entities_str = _convert_entities_to_str(existing_entities)
    topics_of_interest_str = _convert_entities_to_str(topics_of_interest)
    system_prompt = prompts["entity-matching"]["system_prompt"]
    user_prompt = prompts["entity-matching"]["user_prompt"]
    user_contents = user_prompt.format(
        user_profile=user_profile,
        topics_of_interest=topics_of_interest_str,
        entities=entities_str,
    )
    client = genai.Client(api_key=cfg.gemini_api_key)
    contents = f"""
system: {system_prompt}
user:{user_contents}
"""
    response = await client.aio.models.generate_content(
        model=lightrag_cfg.lightrag_model,
        contents=[contents],
        config=types.GenerateContentConfig(
            response_schema=EntityList, response_mime_type="application/json"
        ),
    )
    entities = json.loads(response.text)
    entities_with_score = [
        EntityWithScore(entity=e["entity"], score=e["score"], reasoning=e["reasoning"])
        for e in entities["entities"]
    ]
    return EntityList(entities=entities_with_score)


if __name__ == "__main__":
    topics_of_interest = [
        Entity(
            name="AI",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Automation",
            type="category",
            description="Process automation and workflow optimization",
        ),
    ]
    entity_list = asyncio.run(
        match_entities_with_lightrag(
            Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full"),
            MatchQuery(
                user_profile="I am a software engineer interested in automation and Robotics",
                topics_of_interest=topics_of_interest,
                entities=["category"],
                entities_limit=30,
            ),
        )
    )
    for entity_type, entity_list in entity_list.entity_dict.items():
        print("# ", entity_type)
        for entity in entity_list.entities:
            print("- ", entity.entity, entity.score, entity.reasoning)

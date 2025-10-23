import asyncio
from pathlib import Path
from lightrag import LightRAG
from collections import defaultdict

import pandas as pd
import numpy as np

from graphrag_kb_server.model.search.match_query import MatchQuery, MatchOutput
from graphrag_kb_server.model.search.entity import Entity, EntityList, EntityWithScore
from graphrag_kb_server.service.lightrag.lightrag_centrality import (
    get_sorted_centrality_scores_as_pd,
)
from graphrag_kb_server.prompt_loader import prompts
from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.config import lightrag_cfg
from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.db.db_persistence_expanded_entities import (
    get_expanded_entities,
    insert_expanded_entities,
)
from graphrag_kb_server.logger import logger


def _convert_df_to_entities(
    df: pd.DataFrame, max_description_length: int = 256
) -> list[Entity]:
    return [
        Entity(name=e[0], type=e[1], description=e[2][:max_description_length])
        for e in zip(df["entity_id"], df["entity_type"], df["description"])
    ]


SCORE_THRESHOLD = 0.5


async def match_entities_with_lightrag(
    project_dir: Path, query: MatchQuery
) -> MatchOutput:
    logger.info(f"Matching entities with lightrag for query: {query}")
    if (
        matched_output_from_db := await get_expanded_entities(project_dir, query)
    ) is not None:
        return matched_output_from_db

    entity_types, entities_limit = query.entity_types, query.entities_limit
    df = await get_sorted_centrality_scores_as_pd(project_dir)
    df = df[df["entity_type"].isin(entity_types)][:entities_limit]
    all_entities = _convert_df_to_entities(df)
    entity_list = await match_entities(query, all_entities)
    entity_list = [
        entity
        for entity in entity_list.entities
        if entity.score > query.score_threshold
    ]
    entity_list = await _dedupe_entities(project_dir, entity_list)
    # Convert to format {entity_type: EntityList}
    entity_dict = defaultdict(list)
    entity_type_dict = {e.name: e.type for e in all_entities}
    for entity in entity_list:
        if entity.entity in entity_type_dict:
            entity_dict[entity_type_dict[entity.entity]].append(entity)
    entity_dict = {e[0]: EntityList(entities=e[1]) for e in entity_dict.items()}
    matched_output = MatchOutput(entity_dict=entity_dict)
    await insert_expanded_entities(project_dir, query, matched_output)
    return matched_output


async def _dedupe_entities(
    project_dir: Path, entities: list[EntityWithScore], similarity_threshold=0.51
) -> list[EntityWithScore]:
    rag: LightRAG = await initialize_rag(project_dir)
    embeddings = [rag.entities_vdb.embedding_func(entity.entity) for entity in entities]
    embeddings = await asyncio.gather(*embeddings)
    X = np.vstack(embeddings).astype(np.float32)

    norms = np.linalg.norm(X, axis=1, keepdims=True)
    X = X / np.maximum(norms, 1e-12)

    S = X @ X.T

    np.fill_diagonal(S, -np.inf)
    comparison_matrix = S > similarity_threshold
    remove_indices = set()
    for i in range(len(comparison_matrix)):
        if i in remove_indices:
            # i was already removed due to similarity with an even earlier item;
            # skip it entirely so it doesn't protect later duplicates.
            continue
        for j in range(i + 1, len(comparison_matrix)):
            if comparison_matrix[i, j]:
                remove_indices.add(j)
    deduped = [e for i, e in enumerate(entities) if i not in remove_indices]
    if len(deduped) < 2:
        # Return at least two entities
        return entities
    return deduped


def _convert_entities_to_str(entities: list[Entity]) -> str:
    return "\n".join(
        [f"- {entity.name}\n{entity.description[:150]}" for entity in entities]
    )


async def match_entities(
    query: MatchQuery, existing_entities: list[Entity]
) -> EntityList:
    user_profile, topics_of_interest, question = (
        query.user_profile,
        query.topics_of_interest,
        query.question,
    )
    entities_str = _convert_entities_to_str(existing_entities)
    topics_of_interest_str = _convert_entities_to_str(topics_of_interest)
    system_prompt = prompts["entity-matching"]["system_prompt"]
    user_prompt = prompts["entity-matching"]["user_prompt"]
    user_contents = user_prompt.format(
        question=question if question else "",
        user_profile=user_profile,
        topics_of_interest=topics_of_interest_str,
        entities=entities_str,
    )
    entities = await structured_completion(
        system_prompt, user_contents, EntityList, model=lightrag_cfg.lightrag_lite_model
    )
    entities_with_score = [
        EntityWithScore(
            entity=e["entity"],
            score=e["score"],
            reasoning=e["reasoning"],
            abstraction=e["abstraction"],
        )
        for e in entities["entities"]
    ]
    deduped = {}
    for entity in entities_with_score:
        if not deduped.get(entity.entity):
            deduped[entity.entity] = entity
    entities_with_score = list(deduped.values())
    entity_list = EntityList(entities=entities_with_score)

    return entity_list


if __name__ == "__main__":
    topics_of_interest = [
        Entity(
            name="Artificial Intelligence (AI)",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Technology",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Java",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="AI",
            type="category",
            description="Artificial Intelligence and Machine Learning",
        ),
        Entity(
            name="Business",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Applications",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Digital Transformation",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Cloud",
            type="category",
            description="Process automation and workflow optimization",
        ),
        Entity(
            name="Compliance",
            type="category",
            description="Process automation and workflow optimization",
        ),
    ]

    def test_matching():
        entity_list = asyncio.run(
            match_entities_with_lightrag(
                Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full"),
                MatchQuery(
                    question="How can I use AI to improve my automation and achieve truly autonomous systems?",
                    user_profile="I am a software engineer interested in automation and Robotics",
                    topics_of_interest=tuple(topics_of_interest),
                    entity_types=tuple(["category"]),
                    entities_limit=30,
                ),
            )
        )
        for entity_type, entity_list in entity_list.entity_dict.items():
            print("# ", entity_type)
            for entity in entity_list.entities:
                print(
                    "- ",
                    entity.entity,
                    entity.score,
                    entity.reasoning,
                    entity.abstraction,
                )

    def test_deduplication():
        entities_with_score = [
            EntityWithScore(
                entity=e.name,
                score=1.0,
                reasoning="",
                abstraction="high-level",
            )
            for e in topics_of_interest
        ]
        deduped = asyncio.run(
            _dedupe_entities(
                Path("/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full"),
                entities_with_score,
            )
        )
        for entity in deduped:
            print(entity.entity)

    test_matching()

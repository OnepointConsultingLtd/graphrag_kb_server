from typing import Union
from dataclasses import dataclass

from graphrag.language_model.providers.fnllm.models import OpenAIEmbeddingFNLLM
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.index.operations.summarize_communities.typing import CommunityReport
from graphrag.data_model.relationship import Relationship
from graphrag.data_model.entity import Entity
from graphrag.data_model.text_unit import TextUnit


@dataclass
class ContextBuilderData:
    text_embedder: OpenAIEmbeddingFNLLM
    reports: list[CommunityReport]
    entities: list[Entity]
    relationships: list[Relationship]
    text_units: list[TextUnit]
    covariates: Union[dict, None]
    description_embedding_store: LanceDBVectorStore

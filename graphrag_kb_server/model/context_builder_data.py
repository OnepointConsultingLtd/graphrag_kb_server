from typing import Union
from dataclasses import dataclass

from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.index.operations.summarize_communities.typing import CommunityReport
from graphrag.model.relationship import Relationship
from graphrag.model.entity import Entity
from graphrag.model.text_unit import TextUnit


@dataclass
class ContextBuilderData:
    text_embedder: OpenAIEmbedding
    reports: list[CommunityReport]
    entities: list[Entity]
    relationships: list[Relationship]
    text_units: list[TextUnit]
    covariates: Union[dict, None]
    description_embedding_store: LanceDBVectorStore

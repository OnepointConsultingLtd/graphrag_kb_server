from typing import Final
from pathlib import Path
from pydantic import BaseModel, Field

from graphrag_kb_server.model.engines import Engine


DEFAULT_TOPIC_LIMIT: Final[int] = 20


class Topic(BaseModel):
    name: str = Field(..., description="The name of the topic")
    description: str = Field(..., description="The description of the topic")
    type: str = Field(..., description="The type of th topic")
    questions: list[str] = Field(default=[], description="The questions of the topic")


class Topics(BaseModel):
    topics: list[Topic] = Field(..., description="The topics of the project")


class SimilarityTopic(Topic):
    probability: float = Field(..., description="The probability that the path is reached on a random walk")


class SimilarityTopics(BaseModel):
    topics: list[SimilarityTopic] = Field(..., description="The topics of the project")


class TopicsRequest(BaseModel):
    limit: int = Field(
        default=DEFAULT_TOPIC_LIMIT, description="The number of topics to generate"
    )
    project_dir: Path = Field(..., description="The project directory")
    engine: Engine = Field(..., description="The engine to use")
    add_questions: bool = Field(
        default=False, description="Whether to add questions to the topics"
    )
    entity_type_filter: str = Field(
        default="category",
        description="The entity type to filter by. Only used for LightRAG",
    )


class SimilarityTopicsRequest(BaseModel):
    project_dir: Path = Field(..., description="The project directory")
    source: str = Field(..., description="The source entity to find related entities for")
    text: str = Field(..., description="The text to find related entities for")
    samples: int = Field(default=50000, description="Number of random walk samples to perform")
    path_length: int = Field(default=5, description="Length of each random walk path")
    k: int = Field(default=8, description="Number of top related entities to return")
    restart_prob: float = Field(default=0.15, description="Probability of restarting walk at source node")
    runs: int = Field(default=10, description="Number of independent runs to average results")
    engine: Engine = Field(default=Engine.LIGHTRAG, description="The engine to use")

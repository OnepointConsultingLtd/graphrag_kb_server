from typing import Final
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum

from graphrag_kb_server.model.engines import Engine


DEFAULT_TOPIC_LIMIT: Final[int] = 20


class Topic(BaseModel):
    name: str = Field(..., description="The name of the topic")
    description: str = Field(..., description="The description of the topic")
    type: str = Field(..., description="The type of th topic")
    questions: list[str] = Field(default=[], description="The questions of the topic")

    def markdown(self) -> str:
        return f"""
# {self.name}

## Type: {self.type}

## Description:
{self.description}
"""


class Topics(BaseModel):
    topics: list[Topic] = Field(..., description="The topics of the project")


class TopicQuestion(BaseModel):
    name: str = Field(..., description="The name of the topic")
    questions: list[str] = Field(default=[], description="The questions of the topic")


class TopicQuestions(BaseModel):
    topic_questions: list[TopicQuestion] = Field(
        default=[], description="The questions of the topic"
    )


class SimilarityTopic(Topic):
    probability: float = Field(
        ..., description="The probability that the path is reached on a random walk"
    )

    def markdown(self) -> str:
        return f"""
# {self.name}

## Type: {self.type}

## Description:
{self.description}

## Probability: {self.probability}
"""


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
    topics: list[str] = Field(
        default=[], description="The topics for which questions should be generated"
    )
    deduplicate_topics: bool = Field(
        default=False, description="Whether to deduplicate the topics"
    )

    def __hash__(self) -> int:
        """Make TopicsRequest hashable by converting all fields to hashable types."""
        # Convert Path to string for hashing
        project_dir_str = str(self.project_dir)

        # Convert list to tuple for hashing (tuples are hashable)
        topics_tuple = tuple(self.topics)

        # Create a tuple of all hashable field values
        hashable_fields = (
            self.limit,
            project_dir_str,
            self.engine,
            self.add_questions,
            self.entity_type_filter,
            topics_tuple,
            self.deduplicate_topics,
        )

        return hash(hashable_fields)


class SimilarityTopicsMethod(Enum):
    RANDOM_WALK = "random_walk"
    NEAREST_NEIGHBORS = "nearest_neighbors"

    @classmethod
    def from_string(cls, value: str) -> "SimilarityTopicsMethod":
        """Convert a string to SimilarityTopicsMethod, defaulting to RANDOM_WALK if invalid."""
        try:
            return cls(value)
        except ValueError:
            return cls.RANDOM_WALK


class SimilarityTopicsRequest(BaseModel):
    project_dir: Path = Field(..., description="The project directory")
    source: str = Field(
        ..., description="The source entity to find related entities for"
    )
    text: str = Field(..., description="The text to find related entities for")
    samples: int = Field(
        default=50000, description="Number of random walk samples to perform"
    )
    path_length: int = Field(default=5, description="Length of each random walk path")
    k: int = Field(default=8, description="Number of top related entities to return")
    restart_prob: float = Field(
        default=0.15, description="Probability of restarting walk at source node"
    )
    runs: int = Field(
        default=10, description="Number of independent runs to average results"
    )
    engine: Engine = Field(default=Engine.LIGHTRAG, description="The engine to use")
    topics_prompt: str = Field(
        default="", description="The prompt to post process the generated topics"
    )
    deduplicate_topics: bool = Field(
        default=False, description="Whether to deduplicate the topics"
    )
    use_cosine: bool = Field(
        default=True, description="Whether to use cosine similarity"
    )
    method: SimilarityTopicsMethod = Field(
        default=SimilarityTopicsMethod.NEAREST_NEIGHBORS,
        description="The method to use",
    )


class QuestionsQuery(BaseModel):
    project_dir: Path = Field(..., description="The project directory")
    engine: Engine = Field(..., description="The engine to use")
    limit: int = Field(..., description="The number of topics to generate")
    entity_type_filter: str = Field(..., description="The entity type to filter by")
    topics: list[str] = Field(..., description="The topics filter list")
    text: str = Field(default="", description="The text to generate questions for")
    system_prompt: str = Field(default="", description="The system prompt to use")

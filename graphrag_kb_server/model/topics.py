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


class TopicsRequest(BaseModel):
    limit: int = Field(default=DEFAULT_TOPIC_LIMIT, description="The number of topics to generate")
    project_dir: Path = Field(..., description="The project directory")
    engine: Engine = Field(..., description="The engine to use")
    add_questions: bool = Field(default=False, description="Whether to add questions to the topics")
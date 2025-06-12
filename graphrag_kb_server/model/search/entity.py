from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str = Field(..., description="The name of the entity")
    type: str = Field(default="category", description="The type of the entity")
    description: str = Field(..., description="The description of the entity")


class EntityWithScore(BaseModel):
    entity: str = Field(..., description="The entity name")
    score: float = Field(
        ..., description="The score of the entity according to the user interests"
    )
    reasoning: str = Field(
        ...,
        description="The reasoning behind the choice of this entity and how why it matches the user interests",
    )


class EntityList(BaseModel):
    entities: list[EntityWithScore] = Field(
        ...,
        description="A sorted list of entity names ordered by relevance according to the user interests",
    )

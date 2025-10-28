from pydantic import BaseModel, Field, ConfigDict

from graphrag_kb_server.model.search.entity import Entity, EntityList


class MatchQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    question: str | None = Field(
        default=None,
        description="The question used to find extra entities. This is optional",
    )
    user_profile: str = Field(
        ..., description="The user profile with some information about the user"
    )
    topics_of_interest: tuple[Entity, ...] = Field(
        ..., description="The topics of interest selected by the user"
    )
    entity_types: tuple[str, ...] = Field(
        default=["category"],
        description="The entities to match with the user profile and topics of interest",
    )
    entities_limit: int = Field(
        default=10, description="The maximum number of entities to return"
    )
    score_threshold: float = Field(
        default=0.5, description="The score threshold for the entities"
    )
    no_cache: bool = Field(
        default=False, description="Whether to bypass the cache and force a new search"
    )


class MatchOutput(BaseModel):
    id: int = Field(default=0, description="The id of the match output")
    model_config = ConfigDict(frozen=True)
    entity_dict: dict[str, EntityList] = Field(
        default={},
        description="A dictionary of entity type names and their corresponding entity lists",
    )


if __name__ == "__main__":
    print(MatchOutput.model_json_schema())

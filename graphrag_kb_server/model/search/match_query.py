from pydantic import BaseModel, Field

from graphrag_kb_server.model.search.entity import Entity, EntityList


class MatchQuery(BaseModel):
    question: str | None = Field(
        default=None,
        description="The question used to find extra entities. This is optional",
    )
    user_profile: str = Field(
        ..., description="The user profile with some information about the user"
    )
    topics_of_interest: list[Entity] = Field(
        ..., description="The topics of interest selected by the user"
    )
    entity_types: list[str] = Field(
        default=["category"],
        description="The entities to match with the user profile and topics of interest",
    )
    entities_limit: int = Field(
        default=10, description="The maximum number of entities to return"
    )


class MatchOutput(BaseModel):
    entity_dict: dict[str, EntityList] = Field(
        default={},
        description="A dictionary of entity names and their corresponding entity lists",
    )
    model_config = {
        'frozen': True  # Pydantic v2 config syntax
    }


if __name__ == "__main__":
    print(MatchOutput.model_json_schema())

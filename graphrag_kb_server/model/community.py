from pydantic import BaseModel, Field


class CommunityDescriptors(BaseModel):
    name: str = Field(..., description="A descriptive name for the community.")
    community_description: str = Field(
        ..., description="A brief summary of this community."
    )
    node_descriptions: list[str] = Field(
        ...,
        description="A list of descriptions for the most relevant nodes in the community.",
    )


class Community(BaseModel):
    name: str = Field(default="", description="A name for the community.")
    community_description: str = Field(
        default="", description="A brief summary of this community."
    )
    node_descriptions: list[str] = Field(
        default="",
        description="A list of descriptions for the most relevant nodes in the community.",
    )
    level: int = Field(description="The level of the community. Indexed from 0.")
    cluster_id: int = Field(description="The id of the community.")
    parent_cluster_id: int = Field(
        description="The id of the parent community. -1 if there is no parent."
    )
    number_of_nodes: int = Field(
        default=-1, description="The number of nodes in the community."
    )
    nodes: list[str] = Field(description="The nodes in the community.")

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    question: str = Field(..., description="The question that was asked.")
    response: str | dict = Field(..., description="The response to the chat request.")
    context: str | None = Field(
        default=None, description="The context used to generate the response."
    )
    entities_context: list[dict] | None = Field(
        default=None, description="The entities context used to generate the response."
    )
    relations_context: list[dict] | None = Field(
        default=None, description="The relations context used to generate the response."
    )
    text_units_context: list[dict] | None = Field(
        default=None,
        description="The text units context used to generate the response.",
    )

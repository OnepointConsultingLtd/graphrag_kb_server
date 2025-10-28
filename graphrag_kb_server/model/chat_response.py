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
    hl_keywords: list[str] | None = Field(
        default=None,
        description="The hl_keywords used to generate the response.",
    )
    ll_keywords: list[str] | None = Field(
        default=None,
        description="The ll_keywords used to generate the response.",
    )


class Reference(BaseModel):
    type: str = Field(description="The type of the reference")
    main_keyword: str = Field(description="The main keyword or topic of the reference")
    file: str = Field(description="The file of the reference")


class ResponseSchema(BaseModel):
    response: str = Field(description="The response to the user's question")
    references: list[Reference] = Field(
        description="The references to the user's question"
    )
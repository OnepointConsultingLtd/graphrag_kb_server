from pydantic import BaseModel, Field
from typing import AsyncIterator


class ChatResponse(BaseModel):
    question: str | None = Field(
        default=None, description="The question that was asked."
    )
    response: str | dict | None = Field(
        default=None,
        description="The response to the chat request. If structured output is enabled, return a dictionary with the response and the references.",
    )
    response_iterator: AsyncIterator[str] | None = Field(
        default=None,
        description="The response iterator to the chat request. If streaming is enabled, return an iterator of strings.",
    )
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
    model_config = {"arbitrary_types_allowed": True}


class Reference(BaseModel):
    type: str = Field(description="The type of the reference")
    main_keyword: str = Field(description="The main keyword or topic of the reference")
    file: str = Field(description="The file of the reference")


class ResponseSchema(BaseModel):
    response: str = Field(description="The response to the user's question")
    references: list[Reference] = Field(
        description="The references to the user's question which are typically documents or files with a path. If there are no references, return an empty list."
    )

from enum import StrEnum
from pydantic import BaseModel, Field
from abc import ABC

from graphrag_kb_server.model.search.match_query import MatchOutput


class RelevanceScore(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_RELEVANT = "not_relevant"


RELEVANCE_SCORE_POINTS_MAP = {
    RelevanceScore.VERY_HIGH: 100,
    RelevanceScore.HIGH: 75,
    RelevanceScore.MEDIUM: 50,
    RelevanceScore.LOW: 25,
    RelevanceScore.NOT_RELEVANT: 0,
}


class DocumentSearchQuery(BaseModel):
    question: str | None = Field(
        ...,
        description="The question used to search for documentss or none in which case the question will be generated from the keywords",
    )
    user_profile: str = Field(
        ..., description="The user profile with some information about the user"
    )
    topics_of_interest: MatchOutput = Field(
        ...,
        description="The output of the expanded entities with the highlevel and lowlevel keywords used to search for documents",
    )
    max_filepath_depth: int = Field(
        default=20,
        description="The maximum depth of the file path to include in the context.",
    )


class SummarisationResponse(BaseModel):
    summary: str = Field(..., description="The summary of the document")
    relevance: str = Field(
        ...,
        description="An explanation of the relevance of the document in the context of the user's interests and the question they are asking (in case the question is provided)",
    )
    relevancy_score: RelevanceScore = Field(
        ...,
        description="The relevancy score of the document in the context of the user's interests and the question they are asking (in case the question is provided)",
    )
    main_keyword: str = Field(
        ...,
        description="The main keyword or topic of the reference",
    )

    def get_relevancy_score_points(self) -> int:
        return RELEVANCE_SCORE_POINTS_MAP[self.relevancy_score]


class SummarisationResponseWithDocument(SummarisationResponse):
    document_path: str = Field(
        ..., description="The document path that the user is asking about"
    )


class AbstractSummarizationRequest(BaseModel, ABC):
    user_profile: str = Field(
        ...,
        description="The user profile with the description of the interests of the user",
    )
    question: str | None = Field(
        ..., description="The question that the user is asking"
    )


class SummarisationRequestWithDocumentPath(AbstractSummarizationRequest):
    document_path: str = Field(
        ..., description="The document path that the user is asking about"
    )


class SummarisationRequest(AbstractSummarizationRequest):
    document: str = Field(
        ..., description="The document content that the user is asking about"
    )


class SummarisationResponse(BaseModel):
    summary: str = Field(
        ...,
        description="The summary of the document. You can use markdown to highlight the most important keywords of the summary in bold characters.",
    )
    relevance: str = Field(
        ...,
        description="""An explanation of the relevance of the document in the context of the user's interests and the question they are asking (in case the question is provided)""",
    )
    relevancy_score: RelevanceScore = Field(
        ...,
        description="The relevancy score of the document in the context of the user's interests and the question they are asking (in case the question is provided)",
    )

    def get_relevancy_score_points(self) -> int:
        return RELEVANCE_SCORE_POINTS_MAP[self.relevancy_score]


class SearchResults(BaseModel):
    documents: list[SummarisationResponseWithDocument] = Field(
        ...,
        description="The documents that are relevant to the user's interests and question",
    )
    response: str = Field(
        ...,
        description="The response to the user's question",
    )

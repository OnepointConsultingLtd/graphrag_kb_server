from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from abc import ABC

from graphrag_kb_server.model.search.keywords import Keywords
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
    model_config = ConfigDict(frozen=True)
    request_id: str = Field(
        default="",
        description="The request ID used to track the request",
    )
    linkedin_profile_url: str = Field(
        ...,
        description="The LinkedIn profile URL of the user",
    )
    organisation_role: str = Field(
        ...,
        description="The organisation role of the user",
    )
    organisation_type: str = Field(
        ...,
        description="The organisation type of the user",
    )
    business_type: str = Field(
        ...,
        description="The business type of the user",
    )
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
    is_search_query: bool = Field(
        default=False,
        description="Whether the query is a search query.",
    )
    biggest_challenge: str | None = Field(
        default=None,
        description="The biggest challenge that the user is facing",
    )
    
    @field_validator('biggest_challenge', mode='before')
    @classmethod
    def clean_biggest_challenge(cls, v: str | None) -> str | None:
        """Remove leading/trailing spaces and trailing dots from biggest_challenge."""
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        # Remove leading and trailing spaces
        cleaned = v.strip()
        # Remove trailing dots
        cleaned = cleaned.rstrip('.')
        cleaned = v.strip()
        return cleaned if cleaned else None
    


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
    request_id: str = Field(
        default="",
        description="The request ID used to track the request. Can be left blank if not provided.",
    )
    documents: list[SummarisationResponseWithDocument] = Field(
        ...,
        description="The documents that are relevant to the user's interests and question",
    )
    response: str = Field(
        ...,
        description="The response to the user's question",
    )
    low_level_keywords: Keywords | None = Field(
        default=None,
        description="The low level keywords that were used to search for the documents",
    )
    high_level_keywords: Keywords | None = Field(
        default=None,
        description="The high level keywords that were used to search for the documents",
    )

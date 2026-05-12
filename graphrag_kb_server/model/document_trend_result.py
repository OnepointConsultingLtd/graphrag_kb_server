from pydantic import BaseModel, Field

from graphrag_kb_server.service.trendiness_research import TrendClass, TrendResult


class DocumentTrendResult(BaseModel):
    document_path: str = Field(description="The path to the document")
    project_id: int = Field(description="The id of the project")
    main_topics: list[str] = Field(description="The main topics of the document")
    trend_class: TrendClass = Field(description="The trend class of the document")
    confidence: float = Field(description="The confidence in the trend class by the model")
    reasoning: str = Field(description="The reasoning for the trend class")
    recent_findings: str = Field(description="The recent findings for the trend class")
    visited_urls: list[str] = Field(description="The URLs that were visited to find the information")

    @classmethod
    def from_trend_result(
        cls, document_path: str, project_id: int, trend_result: TrendResult
    ) -> "DocumentTrendResult":
        return cls(
            document_path=document_path,
            project_id=project_id,
            main_topics=trend_result.main_topics,
            trend_class=trend_result.trend_class,
            confidence=trend_result.confidence,
            reasoning=trend_result.reasoning,
            recent_findings=trend_result.recent_findings,
            visited_urls=trend_result.visited_urls,
        )

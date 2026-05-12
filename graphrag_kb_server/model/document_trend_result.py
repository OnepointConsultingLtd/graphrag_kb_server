from pydantic import BaseModel

from graphrag_kb_server.service.trendiness_research import TrendClass, TrendResult


class DocumentTrendResult(BaseModel):
    document_path: str
    project_id: int
    main_topics: list[str]
    trend_class: TrendClass
    confidence: float
    reasoning: str
    recent_findings: str
    visited_urls: list[str]

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

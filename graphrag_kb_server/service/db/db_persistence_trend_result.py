from datetime import date, datetime, timedelta, timezone

from graphrag_kb_server.model.document_trend_result import DocumentTrendResult, TrendClass
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    fetch_one,
    init_pool,
)
from graphrag_kb_server.service.db.db_persistence_project import TB_PROJECTS


TB_DOCUMENT_TREND_RESULT = "TB_DOCUMENT_TREND_RESULT"


def _utc_datetime_for_comparison(value: datetime | date) -> datetime:
    """Normalize DB timestamps to UTC-aware datetimes so expiry math works reliably."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, datetime):
        raise TypeError(f"UPDATED_AT must be datetime-like, got {type(value)!r}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _expiry_timedelta(days: object) -> timedelta:
    """Coerce websocket/JSON payloads (often str) into a timedelta for expiry checks."""
    if isinstance(days, bool):
        raise TypeError("expiry_period_in_days must be numeric, not bool")
    if isinstance(days, float):
        n = int(days)
    elif isinstance(days, int):
        n = days
    else:
        try:
            n = int(days)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"expiry_period_in_days must be integral, got {type(days)!r}"
            ) from exc
    return timedelta(days=max(0, n))


async def create_document_trend_result_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_DOCUMENT_TREND_RESULT} (
    ID              SERIAL      NOT NULL,
    PROJECT_ID      INTEGER     NOT NULL,
    DOCUMENT_PATH   TEXT        NOT NULL,
    MAIN_TOPICS     TEXT[]      NOT NULL,
    TREND_CLASS     VARCHAR(20) NOT NULL,
    CONFIDENCE      FLOAT       NOT NULL,
    REASONING       TEXT        NOT NULL,
    RECENT_FINDINGS TEXT        NOT NULL,
    VISITED_URLS    TEXT[]      NOT NULL,
    CREATED_AT      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    UNIQUE (DOCUMENT_PATH, PROJECT_ID),
    CONSTRAINT PROJECT_ID_FK
        FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID)
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_document_trend_result_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_DOCUMENT_TREND_RESULT};
"""
    )


async def insert_document_trend_result(schema_name: str, result: DocumentTrendResult):
    """Upsert a trend result. Re-inserting for the same (document_path, project_id) refreshes all fields and resets UPDATED_AT."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
INSERT INTO {schema_name}.{TB_DOCUMENT_TREND_RESULT}
    (DOCUMENT_PATH, PROJECT_ID, MAIN_TOPICS, TREND_CLASS, CONFIDENCE, REASONING, RECENT_FINDINGS, VISITED_URLS)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (DOCUMENT_PATH, PROJECT_ID) DO UPDATE
    SET MAIN_TOPICS     = EXCLUDED.MAIN_TOPICS,
        TREND_CLASS     = EXCLUDED.TREND_CLASS,
        CONFIDENCE      = EXCLUDED.CONFIDENCE,
        REASONING       = EXCLUDED.REASONING,
        RECENT_FINDINGS = EXCLUDED.RECENT_FINDINGS,
        VISITED_URLS    = EXCLUDED.VISITED_URLS,
        UPDATED_AT      = now();
""",
            result.document_path,
            result.project_id,
            result.main_topics,
            result.trend_class.value,
            result.confidence,
            result.reasoning,
            result.recent_findings,
            result.visited_urls,
        )


async def get_document_trend_result_by_path(
    schema_name: str,
    document_path: str,
    project_name: str,
    expiry_period_in_days: object,
) -> DocumentTrendResult | None:
    """Return the cached trend result for a document if it has not expired.

    If a row exists but its UPDATED_AT is older than expiry_period_in_days, the
    row is deleted and None is returned so callers know to re-assess.
    """
    row = await fetch_one(
        f"""
SELECT DOCUMENT_PATH, PROJECT_ID, MAIN_TOPICS, TREND_CLASS, CONFIDENCE,
       REASONING, RECENT_FINDINGS, VISITED_URLS, DT.UPDATED_AT
FROM {schema_name}.{TB_DOCUMENT_TREND_RESULT} DT
INNER JOIN {schema_name}.{TB_PROJECTS} P ON DT.PROJECT_ID = P.ID
WHERE DOCUMENT_PATH = $1 AND P.NAME = $2;
""",
        document_path,
        project_name,
    )

    if row is None:
        return None

    updated_at = _utc_datetime_for_comparison(row["updated_at"])

    max_age = _expiry_timedelta(expiry_period_in_days)

    if datetime.now(tz=timezone.utc) - updated_at > max_age:
        await _delete_trend_result(schema_name, document_path, project_name)
        return None

    return DocumentTrendResult(
        document_path=row["document_path"],
        project_id=row["project_id"],
        main_topics=list(row["main_topics"]),
        trend_class=TrendClass(row["trend_class"]),
        confidence=row["confidence"],
        reasoning=row["reasoning"],
        recent_findings=row["recent_findings"],
        visited_urls=list(row["visited_urls"]),
    )


async def _delete_trend_result(schema_name: str, document_path: str, project_name: str):
    await execute_query(
        f"""
DELETE FROM {schema_name}.{TB_DOCUMENT_TREND_RESULT}
WHERE DOCUMENT_PATH = $1 AND PROJECT_ID = (SELECT ID FROM {schema_name}.{TB_PROJECTS} WHERE NAME = $2);
""",
        document_path,
        project_name,
    )

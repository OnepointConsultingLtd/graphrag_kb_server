import re
from datetime import date, datetime, time, timedelta

from graphrag_kb_server.service.db.connection_pool import fetch_all

SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def get_week_window(reference_date: date) -> tuple[date, date]:
    """Return the previous full Monday-Sunday week relative to the reference date.

    Args:
        reference_date: The day the report runs on.

    Returns:
        A tuple (week_start, week_end_exclusive), where week_start is a Monday and
        week_end_exclusive is the following Monday.
    """
    current_week_monday = reference_date - timedelta(days=reference_date.weekday())
    return current_week_monday - timedelta(days=7), current_week_monday


def validate_schema_name(schema_name: str) -> str:
    """Validate a schema name that is interpolated into SQL, to prevent SQL injection.

    Raises:
        ValueError: If the schema name contains characters other than letters, digits and underscores.
    """
    if not SCHEMA_NAME_PATTERN.match(schema_name):
        raise ValueError(f"Invalid schema name: {schema_name!r}")
    return schema_name


def to_start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min)


async def fetch_weekly_activity(schema_name: str, week_start: date, week_end_exclusive: date) -> list[dict]:
    """Fetch all searches with a LinkedIn profile performed in [week_start, week_end_exclusive)."""
    schema = validate_schema_name(schema_name)
    records = await fetch_all(
        f"""
        SELECT linkedin_profile_url, user_role, user_industry, user_organisation_type,
               user_business_type, topic_1, topic_2, topic_3, biggest_challenge,
               created_at, created_at::date AS search_date
        FROM {schema}.TB_SEARCH_HISTORY
        WHERE active = TRUE
          AND linkedin_profile_url IS NOT NULL AND linkedin_profile_url <> ''
          AND created_at >= $1 AND created_at < $2
        ORDER BY created_at
        """,
        to_start_of_day(week_start),
        to_start_of_day(week_end_exclusive),
    )
    return [dict(record) for record in records]


async def fetch_first_seen_dates(schema_name: str, linkedin_profile_urls: list[str]) -> dict[str, date]:
    """Return the date of the first ever search for each given LinkedIn profile URL."""
    if not linkedin_profile_urls:
        return {}
    schema = validate_schema_name(schema_name)
    records = await fetch_all(
        f"""
        SELECT linkedin_profile_url, MIN(created_at)::date AS first_seen
        FROM {schema}.TB_SEARCH_HISTORY
        WHERE active = TRUE AND linkedin_profile_url = ANY($1::text[])
        GROUP BY linkedin_profile_url
        """,
        linkedin_profile_urls,
    )
    return {record["linkedin_profile_url"]: record["first_seen"] for record in records}

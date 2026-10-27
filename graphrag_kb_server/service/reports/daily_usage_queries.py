from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from graphrag_kb_server.service.db.connection_pool import fetch_all
from graphrag_kb_server.service.reports.weekly_usage_queries import to_start_of_day, validate_schema_name

UK_TIMEZONE = ZoneInfo("Europe/London")


def get_uk_today(now: datetime | None = None) -> date:
    """Return the current calendar date in the UK (handles GMT/BST), regardless of the server's timezone.

    Args:
        now: Timezone-aware moment to convert; defaults to the current time.
    """
    return (now or datetime.now(UK_TIMEZONE)).astimezone(UK_TIMEZONE).date()


async def fetch_new_users_activity(schema_name: str, day: date) -> list[dict]:
    """Fetch the searches performed on the given day by users who never searched on any previous day.

    Uses NOT EXISTS rather than NOT IN so that a NULL profile URL in the history cannot make the
    query return no rows.
    """
    schema = validate_schema_name(schema_name)
    records = await fetch_all(
        f"""
        SELECT h.linkedin_profile_url, h.user_role, h.user_industry, h.user_organisation_type,
               h.user_business_type, h.topic_1, h.topic_2, h.topic_3, h.biggest_challenge,
               h.created_at, h.created_at::date AS search_date
        FROM {schema}.TB_SEARCH_HISTORY h
        WHERE h.active = TRUE
          AND h.linkedin_profile_url IS NOT NULL AND h.linkedin_profile_url <> ''
          AND h.created_at >= $1 AND h.created_at < $2
          AND NOT EXISTS (
              SELECT 1 FROM {schema}.TB_SEARCH_HISTORY previous
              WHERE previous.active = TRUE
                AND previous.linkedin_profile_url = h.linkedin_profile_url
                AND previous.created_at < $1
          )
        ORDER BY h.created_at
        """,
        to_start_of_day(day),
        to_start_of_day(day + timedelta(days=1)),
    )
    return [dict(record) for record in records]

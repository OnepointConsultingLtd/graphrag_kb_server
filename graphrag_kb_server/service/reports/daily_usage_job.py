import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from graphrag_kb_server.config import report_cfg
from graphrag_kb_server.service.db.connection_pool import close_connection_pool
from graphrag_kb_server.service.html_to_pdf import async_convert_html_to_pdf
from graphrag_kb_server.service.reports.daily_usage_queries import fetch_new_users_activity, get_uk_today
from graphrag_kb_server.service.reports.daily_usage_render import (
    format_report_day,
    render_daily_email_body,
    render_daily_report_html,
)
from graphrag_kb_server.service.reports.email_sender import async_send_email_with_attachment
from graphrag_kb_server.service.reports.weekly_usage_job import validate_report_config
from graphrag_kb_server.service.reports.weekly_usage_model import WeeklyReport, build_weekly_report

logger = logging.getLogger(__name__)


def build_daily_report(rows: list[dict], day: date) -> WeeklyReport:
    """Build a one day report where every user in the rows is flagged as new.

    The rows are expected to come from fetch_new_users_activity, so each user is new by construction.
    The day is stored as the report's window [day, day + 1).
    """
    first_seen_dates = {row["linkedin_profile_url"]: day for row in rows}
    return build_weekly_report(rows, first_seen_dates, day, day + timedelta(days=1))


async def run_daily_report(day: Optional[date] = None) -> Optional[WeeklyReport]:
    """Email the users who searched for the first time on the given day. Nothing is sent without new users.

    Args:
        day: Day to report on; defaults to today in the UK.

    Returns:
        The report, or None if there were no new users and no email was sent.
    """
    validate_report_config(report_cfg)
    report_day = day or get_uk_today()
    rows = await fetch_new_users_activity(report_cfg.schema_name, report_day)
    if not rows:
        logger.info(f"No new users on {report_day.isoformat()}, daily report not sent")
        return None
    report = build_daily_report(rows, report_day)
    pdf_bytes = await async_convert_html_to_pdf(render_daily_report_html(report))
    text_body, html_body = render_daily_email_body(report)
    await async_send_email_with_attachment(
        report_cfg,
        f"Clustre new users report {format_report_day(report)}",
        text_body,
        html_body,
        f"clustre_new_users_{format_report_day(report)}.pdf",
        pdf_bytes,
    )
    logger.info(f"Daily report sent to {len(report_cfg.recipients)} recipient(s) for {format_report_day(report)}")
    return report


async def _main() -> None:
    try:
        await run_daily_report()
    finally:
        await close_connection_pool()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()

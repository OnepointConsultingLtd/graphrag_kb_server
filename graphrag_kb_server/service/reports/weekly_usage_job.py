import asyncio
import logging
from datetime import date
from typing import Optional

from graphrag_kb_server.config import ReportConfig, report_cfg
from graphrag_kb_server.service.db.connection_pool import close_connection_pool
from graphrag_kb_server.service.html_to_pdf import async_convert_html_to_pdf
from graphrag_kb_server.service.reports.email_sender import async_send_email_with_attachment
from graphrag_kb_server.service.reports.weekly_usage_model import WeeklyReport, build_weekly_report
from graphrag_kb_server.service.reports.weekly_usage_queries import (
    fetch_first_seen_dates,
    fetch_weekly_activity,
    get_week_window,
)
from graphrag_kb_server.service.reports.weekly_usage_render import (
    format_week_range,
    render_email_body,
    render_report_html,
)

logger = logging.getLogger(__name__)


def validate_report_config(config: type[ReportConfig]) -> None:
    """Raise ValueError listing every missing setting required to send the report."""
    missing = []
    if not config.recipients:
        missing.append("REPORT_RECIPIENTS")
    if not config.smtp_host:
        missing.append("SMTP_HOST")
    if not config.smtp_from:
        missing.append("SMTP_FROM (or SMTP_USER)")
    if missing:
        raise ValueError(f"Missing report configuration: {', '.join(missing)}")


async def build_report_for_week(schema_name: str, week_start: date, week_end_exclusive: date) -> WeeklyReport:
    """Load the week's searches and the first-seen dates of their users, and build the report."""
    rows = await fetch_weekly_activity(schema_name, week_start, week_end_exclusive)
    profile_urls = sorted({row["linkedin_profile_url"] for row in rows})
    first_seen_dates = await fetch_first_seen_dates(schema_name, profile_urls)
    return build_weekly_report(rows, first_seen_dates, week_start, week_end_exclusive)


async def run_weekly_report(reference_date: Optional[date] = None) -> WeeklyReport:
    """Build the report for the previous Monday-Sunday week and email it as a PDF attachment.

    Args:
        reference_date: Day the report runs on; defaults to today.
    """
    validate_report_config(report_cfg)
    week_start, week_end_exclusive = get_week_window(reference_date or date.today())
    report = await build_report_for_week(report_cfg.schema_name, week_start, week_end_exclusive)
    pdf_bytes = await async_convert_html_to_pdf(render_report_html(report))
    text_body, html_body = render_email_body(report)
    await async_send_email_with_attachment(
        report_cfg,
        f"Clustre weekly usage report {format_week_range(report)}",
        text_body,
        html_body,
        f"clustre_usage_{week_start.isoformat()}.pdf",
        pdf_bytes,
    )
    logger.info(f"Weekly report sent to {len(report_cfg.recipients)} recipient(s) for {format_week_range(report)}")
    return report


async def _main() -> None:
    try:
        await run_weekly_report()
    finally:
        await close_connection_pool()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()

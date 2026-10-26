from datetime import timedelta
from html import escape

from graphrag_kb_server.service.reports.weekly_usage_model import UserDayActivity, WeeklyReport

REPORT_CSS = """
<style>
  body.report { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #222; }
  body.report h1 { font-size: 18pt; margin-bottom: 2pt; }
  body.report h2 { font-size: 12pt; margin-top: 16pt; border-bottom: 1px solid #999; }
  body.report table { border-collapse: collapse; width: 100%; }
  body.report th, body.report td { border: 1px solid #ccc; padding: 3pt 5pt; text-align: left; vertical-align: top; }
  body.report th { background: #f0f0f0; }
  body.report .new { color: #0a7d32; font-weight: bold; }
</style>
"""


def format_week_range(report: WeeklyReport) -> str:
    """Human readable inclusive date range of the report, e.g. '2026-10-19 to 2026-10-25'."""
    last_day = report.week_end_exclusive - timedelta(days=1)
    return f"{report.week_start.isoformat()} to {last_day.isoformat()}"


def _render_activity_row(activity: UserDayActivity) -> str:
    url = escape(activity.linkedin_profile_url)
    new_badge = ' <span class="new">NEW</span>' if activity.is_new else ""
    details = ", ".join(
        escape(part)
        for part in (
            activity.user_role,
            activity.user_industry,
            activity.user_organisation_type,
            activity.user_business_type,
        )
        if part
    )
    return (
        f'<tr><td><a href="{url}">{url}</a>{new_badge}</td><td>{details}</td>'
        f"<td>{escape(', '.join(activity.topics))}</td><td>{activity.search_count}</td></tr>"
    )


def render_report_html(report: WeeklyReport) -> str:
    """Render the full report (all users, grouped by day) as an HTML document to be converted to PDF."""
    sections = []
    for day in sorted(report.activity_by_day):
        rows = "".join(_render_activity_row(a) for a in report.activity_by_day[day])
        sections.append(
            f"<h2>{day.strftime('%A %Y-%m-%d')}</h2>"
            f"<table><tr><th>LinkedIn profile</th><th>Profile</th><th>Topics</th><th>Searches</th></tr>{rows}</table>"
        )
    body = "".join(sections) or "<p>No searches were performed this week.</p>"
    return (
        f"<html><head><meta charset='utf-8'><title>Clustre weekly usage</title>{REPORT_CSS}</head>"
        f"<body class='report'><h1>Clustre weekly usage report</h1>"
        f"<p>{format_week_range(report)} &middot; {report.distinct_user_count} users, "
        f"{len(report.new_users_activity)} new</p>{body}</body></html>"
    )


def render_email_body(report: WeeklyReport) -> tuple[str, str]:
    """Render the email body listing only the new users and the days they searched.

    Returns:
        A tuple (plain_text, html).
    """
    new_users = report.new_users_activity
    heading = f"Clustre search usage {format_week_range(report)}"
    if not new_users:
        text = f"{heading}\n\nNo new users this week. Full details are in the attached PDF."
        return text, f"<p><b>{heading}</b></p><p>No new users this week. Full details are in the attached PDF.</p>"

    text_lines = [heading, "", f"{len(new_users)} new user(s):"]
    html_items = []
    for url, activities in new_users.items():
        days = ", ".join(a.search_date.strftime("%a %Y-%m-%d") for a in activities)
        text_lines.append(f"- {url}: {days}")
        html_items.append(f'<li><a href="{escape(url)}">{escape(url)}</a>: {escape(days)}</li>')
    text_lines += ["", "Full details are in the attached PDF."]
    html = (
        f"<p><b>{heading}</b></p><p>{len(new_users)} new user(s):</p><ul>{''.join(html_items)}</ul>"
        "<p>Full details are in the attached PDF.</p>"
    )
    return "\n".join(text_lines), html

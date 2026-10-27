from html import escape

from graphrag_kb_server.service.reports.weekly_usage_model import WeeklyReport
from graphrag_kb_server.service.reports.weekly_usage_render import REPORT_CSS, render_activity_row


def format_report_day(report: WeeklyReport) -> str:
    """ISO date of the single day covered by a daily report."""
    return report.week_start.isoformat()


def render_daily_report_html(report: WeeklyReport) -> str:
    """Render the daily new users as an HTML document to be converted to PDF."""
    rows = "".join(render_activity_row(a) for a in report.activity_by_day.get(report.week_start, []))
    return (
        f"<html><head><meta charset='utf-8'><title>Clustre new users</title>{REPORT_CSS}</head>"
        f"<body class='report'><h1>Clustre new users report</h1>"
        f"<p>{format_report_day(report)} &middot; {len(report.new_users_activity)} new user(s)</p>"
        f"<table><tr><th>LinkedIn profile</th><th>Profile</th><th>Topics</th><th>Biggest challenge</th><th>Searches</th></tr>{rows}</table>"
        "</body></html>"
    )


def render_daily_email_body(report: WeeklyReport) -> tuple[str, str]:
    """Render the email body listing the new users of the day.

    Returns:
        A tuple (plain_text, html).
    """
    new_users = report.new_users_activity
    new_users_challenges = report.new_users_challenges
    heading = f"Clustre new users on {format_report_day(report)}"
    text_lines = [heading, "", f"{len(new_users)} new user(s):"]
    html_items = []
    for url, activities in new_users.items():
        searches = sum(a.search_count for a in activities)
        challenges = " | ".join(new_users_challenges[url])
        challenge_text = f" (biggest challenge: {challenges})" if challenges else ""
        text_lines.append(f"- {url}: {searches} search(es){challenge_text}")
        html_items.append(
            f'<li><a href="{escape(url)}">{escape(url)}</a>: {searches} search(es){escape(challenge_text)}</li>'
        )
    text_lines += ["", "Full details are in the attached PDF."]
    html = (
        f"<p><b>{heading}</b></p><p>{len(new_users)} new user(s):</p><ul>{''.join(html_items)}</ul>"
        "<p>Full details are in the attached PDF.</p>"
    )
    return "\n".join(text_lines), html

from datetime import date

import pytest

from graphrag_kb_server.service.reports.email_sender import build_email_message
from graphrag_kb_server.service.reports.weekly_usage_job import validate_report_config
from graphrag_kb_server.service.reports.weekly_usage_model import build_weekly_report
from graphrag_kb_server.service.reports.weekly_usage_queries import get_week_window, validate_schema_name
from graphrag_kb_server.service.reports.weekly_usage_render import render_email_body, render_report_html

WEEK_START = date(2026, 10, 19)
WEEK_END = date(2026, 10, 26)
NEW_USER = "https://linkedin.com/in/new-user"
RETURNING_USER = "https://linkedin.com/in/returning-user"


def make_row(url, day, **overrides):
    row = {"linkedin_profile_url": url, "search_date": day, "user_role": "CTO", "topic_1": "AI", "topic_2": None}
    row.update(overrides)
    return row


def make_report():
    rows = [
        make_row(NEW_USER, date(2026, 10, 20)),
        make_row(NEW_USER, date(2026, 10, 20), topic_2="Cloud"),
        make_row(NEW_USER, date(2026, 10, 22)),
        make_row(RETURNING_USER, date(2026, 10, 21)),
        make_row(None, date(2026, 10, 21)),
    ]
    first_seen = {NEW_USER: date(2026, 10, 20), RETURNING_USER: date(2026, 1, 5)}
    return build_weekly_report(rows, first_seen, WEEK_START, WEEK_END)


@pytest.mark.parametrize(
    "reference",
    [date(2026, 10, 26), date(2026, 10, 28), date(2026, 11, 1)],
)
def test_week_window_is_previous_monday_to_sunday(reference):
    """Monday, mid-week and Sunday of the same week all map to the previous full week."""
    assert get_week_window(reference) == (WEEK_START, WEEK_END)


def test_week_window_year_boundary():
    assert get_week_window(date(2026, 1, 1)) == (date(2025, 12, 22), date(2025, 12, 29))


def test_validate_schema_name_rejects_injection():
    assert validate_schema_name("gil_fernandes") == "gil_fernandes"
    with pytest.raises(ValueError):
        validate_schema_name("public; DROP TABLE x")


def test_report_flags_new_users_and_groups_by_day():
    report = make_report()
    assert sorted(report.activity_by_day) == [date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22)]
    assert report.distinct_user_count == 2
    first_day_activity = report.activity_by_day[date(2026, 10, 20)][0]
    assert first_day_activity.search_count == 2
    assert first_day_activity.topics == ["AI", "Cloud"]
    assert list(report.new_users_activity) == [NEW_USER]
    assert [a.search_date for a in report.new_users_activity[NEW_USER]] == [date(2026, 10, 20), date(2026, 10, 22)]


def test_user_without_first_seen_is_not_new():
    report = build_weekly_report([make_row(NEW_USER, date(2026, 10, 20))], {}, WEEK_START, WEEK_END)
    assert report.new_users_activity == {}


def test_email_body_lists_only_new_users():
    text, html = render_email_body(make_report())
    assert NEW_USER in text and NEW_USER in html
    assert RETURNING_USER not in text and RETURNING_USER not in html
    assert "2026-10-20" in text and "2026-10-22" in text


def test_email_body_without_new_users():
    empty = build_weekly_report([], {}, WEEK_START, WEEK_END)
    text, _ = render_email_body(empty)
    assert "No new users" in text


def test_report_html_contains_all_users_and_days():
    html = render_report_html(make_report())
    assert NEW_USER in html and RETURNING_USER in html
    assert "2026-10-21" in html
    assert html.count("NEW</span>") == 2  # new user appears on two days


def test_build_email_message_has_pdf_attachment():
    message = build_email_message("from@x.com", ["a@x.com", "b@x.com"], "Subject", "text", "<p>html</p>", "r.pdf", b"%PDF")
    assert message["To"] == "a@x.com, b@x.com"
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "r.pdf"
    assert attachments[0].get_content() == b"%PDF"


def test_validate_report_config_reports_missing_settings():
    class EmptyConfig:
        recipients = []
        smtp_host = None
        smtp_from = None

    with pytest.raises(ValueError, match="REPORT_RECIPIENTS.*SMTP_HOST"):
        validate_report_config(EmptyConfig)

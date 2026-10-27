from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from graphrag_kb_server.service.reports import daily_usage_job
from graphrag_kb_server.service.reports.daily_usage_job import build_daily_report, run_daily_report
from graphrag_kb_server.service.reports.daily_usage_queries import get_uk_today
from graphrag_kb_server.service.reports.daily_usage_render import render_daily_email_body, render_daily_report_html

DAY = date(2026, 10, 27)
NEW_USER = "https://linkedin.com/in/new-user"
OTHER_NEW_USER = "https://linkedin.com/in/other-new-user"


def make_rows():
    return [
        {"linkedin_profile_url": NEW_USER, "search_date": DAY, "user_role": "CTO", "topic_1": "AI", "biggest_challenge": "Legacy systems"},
        {"linkedin_profile_url": NEW_USER, "search_date": DAY, "user_role": "CTO", "topic_1": "Cloud"},
        {"linkedin_profile_url": OTHER_NEW_USER, "search_date": DAY, "user_role": "CEO", "topic_1": "AI"},
    ]


def test_build_daily_report_flags_all_users_as_new():
    report = build_daily_report(make_rows(), DAY)
    assert set(report.new_users_activity) == {NEW_USER, OTHER_NEW_USER}
    assert report.new_users_activity[NEW_USER][0].search_count == 2


def test_daily_email_body_lists_users_with_search_counts():
    text, html = render_daily_email_body(build_daily_report(make_rows(), DAY))
    assert "2 new user(s)" in text
    assert f"- {NEW_USER}: 2 search(es)" in text
    assert OTHER_NEW_USER in html


def test_daily_report_includes_biggest_challenge():
    report = build_daily_report(make_rows(), DAY)
    text, _ = render_daily_email_body(report)
    assert f"- {NEW_USER}: 2 search(es) (biggest challenge: Legacy systems)" in text
    assert "Legacy systems" in render_daily_report_html(report)


def test_daily_report_html_contains_users():
    html = render_daily_report_html(build_daily_report(make_rows(), DAY))
    assert NEW_USER in html and OTHER_NEW_USER in html
    assert "2026-10-27" in html


@pytest.mark.parametrize(
    "utc_moment, expected",
    [
        (datetime(2026, 7, 1, 22, 59, tzinfo=timezone.utc), date(2026, 7, 1)),  # 23:59 BST
        (datetime(2026, 7, 1, 23, 30, tzinfo=timezone.utc), date(2026, 7, 2)),  # 00:30 BST next day
        (datetime(2026, 12, 1, 23, 59, tzinfo=timezone.utc), date(2026, 12, 1)),  # 23:59 GMT
    ],
)
def test_get_uk_today_handles_daylight_saving(utc_moment, expected):
    assert get_uk_today(utc_moment) == expected


@pytest.fixture
def mocked_job(monkeypatch):
    monkeypatch.setattr(daily_usage_job, "validate_report_config", lambda config: None)
    send_email = AsyncMock()
    monkeypatch.setattr(daily_usage_job, "async_send_email_with_attachment", send_email)
    monkeypatch.setattr(daily_usage_job, "async_convert_html_to_pdf", AsyncMock(return_value=b"%PDF"))
    return send_email


@pytest.mark.asyncio
async def test_no_email_is_sent_without_new_users(monkeypatch, mocked_job):
    monkeypatch.setattr(daily_usage_job, "fetch_new_users_activity", AsyncMock(return_value=[]))
    assert await run_daily_report(DAY) is None
    mocked_job.assert_not_called()


@pytest.mark.asyncio
async def test_email_is_sent_with_new_users(monkeypatch, mocked_job):
    monkeypatch.setattr(daily_usage_job, "fetch_new_users_activity", AsyncMock(return_value=make_rows()))
    report = await run_daily_report(DAY)
    assert report is not None
    mocked_job.assert_awaited_once()
    assert mocked_job.await_args.args[1] == "Clustre new users report 2026-10-27"
    assert mocked_job.await_args.args[4] == "clustre_new_users_2026-10-27.pdf"

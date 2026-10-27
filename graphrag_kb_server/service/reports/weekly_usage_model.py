from dataclasses import dataclass, field
from datetime import date


@dataclass
class UserDayActivity:
    """Searches performed by one LinkedIn profile on one day."""

    linkedin_profile_url: str
    search_date: date
    search_count: int
    is_new: bool
    user_role: str = ""
    user_industry: str = ""
    user_organisation_type: str = ""
    user_business_type: str = ""
    topics: list[str] = field(default_factory=list)
    biggest_challenges: list[str] = field(default_factory=list)


@dataclass
class WeeklyReport:
    """Usage of the search for one week, grouped by day."""

    week_start: date
    week_end_exclusive: date
    activity_by_day: dict[date, list[UserDayActivity]] = field(default_factory=dict)

    @property
    def new_users_activity(self) -> dict[str, list[UserDayActivity]]:
        """Activity of the new users, keyed by LinkedIn profile URL and ordered by day."""
        new_users: dict[str, list[UserDayActivity]] = {}
        for day in sorted(self.activity_by_day):
            for activity in self.activity_by_day[day]:
                if activity.is_new:
                    new_users.setdefault(activity.linkedin_profile_url, []).append(activity)
        return new_users

    @property
    def new_users_challenges(self) -> dict[str, list[str]]:
        """Distinct biggest challenges of each new user across their days, keyed by LinkedIn profile URL."""
        challenges_by_user: dict[str, list[str]] = {}
        for url, activities in self.new_users_activity.items():
            challenges = challenges_by_user.setdefault(url, [])
            for activity in activities:
                challenges.extend(c for c in activity.biggest_challenges if c not in challenges)
        return challenges_by_user

    @property
    def distinct_user_count(self) -> int:
        return len({a.linkedin_profile_url for acts in self.activity_by_day.values() for a in acts})


def _first_non_empty(values: list) -> str:
    return next((value for value in values if value), "")


def _collect_topics(rows: list[dict]) -> list[str]:
    topics: list[str] = []
    for row in rows:
        for key in ("topic_1", "topic_2", "topic_3"):
            topic = row.get(key)
            if topic and topic not in topics:
                topics.append(topic)
    return topics


def _collect_biggest_challenges(rows: list[dict]) -> list[str]:
    challenges: list[str] = []
    for row in rows:
        challenge = row.get("biggest_challenge")
        if challenge and challenge not in challenges:
            challenges.append(challenge)
    return challenges


def build_weekly_report(
    rows: list[dict],
    first_seen_dates: dict[str, date],
    week_start: date,
    week_end_exclusive: date,
) -> WeeklyReport:
    """Group search rows by day and user, flagging users whose first ever search is within the week.

    Args:
        rows: Search history rows with at least linkedin_profile_url and search_date.
        first_seen_dates: First ever search date per LinkedIn profile URL.
        week_start: First day of the week (inclusive).
        week_end_exclusive: Day after the last day of the week.

    Returns:
        The report. Rows without a LinkedIn profile URL are ignored.
    """
    rows_by_day_and_user: dict[tuple[date, str], list[dict]] = {}
    for row in rows:
        url = row.get("linkedin_profile_url")
        if not url:
            continue
        rows_by_day_and_user.setdefault((row["search_date"], url), []).append(row)

    report = WeeklyReport(week_start=week_start, week_end_exclusive=week_end_exclusive)
    for (day, url), user_rows in sorted(rows_by_day_and_user.items()):
        first_seen = first_seen_dates.get(url)
        is_new = first_seen is not None and week_start <= first_seen < week_end_exclusive
        report.activity_by_day.setdefault(day, []).append(
            UserDayActivity(
                linkedin_profile_url=url,
                search_date=day,
                search_count=len(user_rows),
                is_new=is_new,
                user_role=_first_non_empty([r.get("user_role") for r in user_rows]),
                user_industry=_first_non_empty([r.get("user_industry") for r in user_rows]),
                user_organisation_type=_first_non_empty([r.get("user_organisation_type") for r in user_rows]),
                user_business_type=_first_non_empty([r.get("user_business_type") for r in user_rows]),
                topics=_collect_topics(user_rows),
                biggest_challenges=_collect_biggest_challenges(user_rows),
            )
        )
    return report

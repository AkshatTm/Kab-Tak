from datetime import UTC, date, datetime, time

from app.timer.studyday import study_day
from tests.fakeclock import IST


def local(h: int, m: int, day: int = 2) -> datetime:
    return datetime(2026, 1, day, h, m, tzinfo=IST).astimezone(UTC)


def test_cutoff_boundary() -> None:
    cut = time(4, 0)
    assert study_day(local(3, 59), IST, cut) == date(2026, 1, 1)
    assert study_day(local(4, 0), IST, cut) == date(2026, 1, 2)
    assert study_day(local(0, 30), IST, cut) == date(2026, 1, 1)
    assert study_day(local(23, 59), IST, cut) == date(2026, 1, 2)


def test_midnight_cutoff_is_calendar_day() -> None:
    assert study_day(local(0, 0), IST, time(0, 0)) == date(2026, 1, 2)
    assert study_day(local(23, 59), IST, time(0, 0)) == date(2026, 1, 2)

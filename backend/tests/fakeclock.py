from datetime import UTC, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


class FakeClock:
    """Test clock: starts at 2026-01-01 12:00 UTC (17:30 local), tz fixed at +05:30."""

    tz = IST

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, minutes: float) -> datetime:
        self._now += timedelta(minutes=minutes)
        return self._now

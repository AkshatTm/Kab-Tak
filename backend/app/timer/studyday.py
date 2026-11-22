from datetime import date, datetime, time, timedelta, tzinfo


def study_day(instant: datetime, tz: tzinfo, day_starts_at: time) -> date:
    """D4: the local day, shifted so a task at 00:30 belongs to the previous day (cutoff 04:00)."""
    local = instant.astimezone(tz)
    return (local - timedelta(hours=day_starts_at.hour, minutes=day_starts_at.minute)).date()


def parse_cutoff(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))

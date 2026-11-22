from datetime import UTC, datetime, tzinfo
from typing import Protocol


class Clock(Protocol):
    @property
    def tz(self) -> tzinfo: ...  # the user's local timezone (the sidecar runs locally, D4)

    def now(self) -> datetime: ...  # aware UTC


class SystemClock:
    def __init__(self) -> None:
        self._tz = datetime.now().astimezone().tzinfo or UTC

    @property
    def tz(self) -> tzinfo:
        return self._tz

    def now(self) -> datetime:
        return datetime.now(UTC)

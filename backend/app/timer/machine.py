"""Pure timer state machine (SPEC 2.5). No DB, no I/O, no clock: `now` is always a parameter.

draft -> ready -> running <-> paused -> stopped; stop is legal from running or paused.
All datetimes must be timezone-aware UTC (ValueError otherwise).
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum


class Status(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class TimerError(Exception):
    pass


class InvalidTransition(TimerError):
    pass


class InvalidAt(TimerError):
    pass


@dataclass(frozen=True)
class Span:
    start: datetime
    end: datetime | None


@dataclass(frozen=True)
class Task:
    status: Status
    estimate_min: int | None
    sessions: tuple[Span, ...]
    stopped_at: datetime | None = None  # the instant of stop (may be later than the last span end)


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() != UTC.utcoffset(None):
        raise ValueError("datetime must be timezone-aware UTC")
    return dt


def _expect(task: Task, *allowed: Status, cmd: str) -> None:
    if task.status not in allowed:
        raise InvalidTransition(f"cannot {cmd} a {task.status} task")


def _last_end(task: Task) -> datetime | None:
    return task.sessions[-1].end if task.sessions else None


def _open(task: Task, now: datetime, at: datetime | None) -> datetime:
    """Validate `at` (default now) against now and the lower bound for the current state."""
    now = _utc(now)
    at = now if at is None else _utc(at)
    if at > now:
        raise InvalidAt("at is in the future")
    floor = task.sessions[-1].start if task.status is Status.RUNNING else _last_end(task)
    if floor is not None and at < floor:
        raise InvalidAt("at is before the current span start / last span end")
    return at


def start(task: Task, now: datetime) -> Task:
    _expect(task, Status.READY, cmd="start")
    now = _utc(now)
    return replace(task, status=Status.RUNNING, sessions=(*task.sessions, Span(now, None)))


def resume(task: Task, now: datetime) -> Task:
    _expect(task, Status.PAUSED, cmd="resume")
    at = _open(task, now, None)
    return replace(task, status=Status.RUNNING, sessions=(*task.sessions, Span(at, None)))


def _close(task: Task, at: datetime) -> tuple[Span, ...]:
    *done, cur = task.sessions
    return (*done, Span(cur.start, at))


def pause(task: Task, now: datetime, at: datetime | None = None) -> Task:
    _expect(task, Status.RUNNING, cmd="pause")
    at = _open(task, now, at)
    return replace(task, status=Status.PAUSED, sessions=_close(task, at))


def stop(task: Task, now: datetime, at: datetime | None = None) -> Task:
    _expect(task, Status.RUNNING, Status.PAUSED, cmd="stop")
    at = _open(task, now, at)
    sessions = _close(task, at) if task.status is Status.RUNNING else task.sessions
    return replace(task, status=Status.STOPPED, sessions=sessions, stopped_at=at)


def active_min(task: Task, now: datetime) -> float:
    """Sum of closed spans plus the open span up to `now`, in float minutes."""
    now = _utc(now)
    return sum(((s.end or now) - s.start).total_seconds() for s in task.sessions) / 60


def wall_min(task: Task) -> float:
    """stopped_at minus the first span start; only meaningful once stopped."""
    if task.stopped_at is None or not task.sessions:
        raise InvalidTransition("wall_min needs a stopped task")
    return (task.stopped_at - task.sessions[0].start).total_seconds() / 60

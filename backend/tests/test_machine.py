from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.timer.machine import (
    InvalidAt,
    InvalidTransition,
    Span,
    Status,
    Task,
    TimerError,
    active_min,
    pause,
    resume,
    start,
    stop,
    wall_min,
)

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
IST = timezone(timedelta(hours=5, minutes=30))


def m(n: float) -> datetime:
    return T0 + timedelta(minutes=n)


def mk(status: Status) -> Task:
    """A task in `status`; its open/last span started at m(0) (ended at m(5) if not running)."""
    if status is Status.DRAFT:
        return Task(status, None, ())
    if status is Status.READY:
        return Task(status, 30, ())
    if status is Status.RUNNING:
        return Task(status, 30, (Span(m(0), None),))
    if status is Status.PAUSED:
        return Task(status, 30, (Span(m(0), m(5)),))
    return Task(status, 30, (Span(m(0), m(5)),), stopped_at=m(5))


COMMANDS = {"start": start, "pause": pause, "resume": resume, "stop": stop}
OK = {
    (Status.READY, "start"): Status.RUNNING,
    (Status.RUNNING, "pause"): Status.PAUSED,
    (Status.PAUSED, "resume"): Status.RUNNING,
    (Status.RUNNING, "stop"): Status.STOPPED,
    (Status.PAUSED, "stop"): Status.STOPPED,
}


@pytest.mark.parametrize("status", list(Status))
@pytest.mark.parametrize("cmd", list(COMMANDS))
def test_every_pair(status: Status, cmd: str) -> None:
    task = mk(status)
    if (status, cmd) in OK:
        assert COMMANDS[cmd](task, m(10)).status is OK[(status, cmd)]
    else:
        with pytest.raises(InvalidTransition):
            COMMANDS[cmd](task, m(10))


def test_errors_share_base() -> None:
    assert issubclass(InvalidTransition, TimerError)
    assert issubclass(InvalidAt, TimerError)


def test_inputs_not_mutated() -> None:
    t = mk(Status.READY)
    start(t, m(1))
    assert t.status is Status.READY and t.sessions == ()


def test_at_before_span_start() -> None:
    with pytest.raises(InvalidAt):
        pause(mk(Status.RUNNING), m(10), at=m(-1))
    with pytest.raises(InvalidAt):
        stop(mk(Status.RUNNING), m(10), at=m(-1))


def test_at_before_last_span_end_when_stopping_from_paused() -> None:
    with pytest.raises(InvalidAt):
        stop(mk(Status.PAUSED), m(10), at=m(4))


def test_at_in_future() -> None:
    with pytest.raises(InvalidAt):
        pause(mk(Status.RUNNING), m(10), at=m(11))
    with pytest.raises(InvalidAt):
        stop(mk(Status.PAUSED), m(10), at=m(11))


def test_at_backdates_pause() -> None:
    t = pause(mk(Status.RUNNING), m(10), at=m(7))
    assert active_min(t, m(10)) == 7


def test_start_or_resume_before_last_end_is_invalid() -> None:
    with pytest.raises(InvalidAt):
        resume(mk(Status.PAUSED), m(3))


def test_lifecycle_with_pause() -> None:
    t = start(mk(Status.READY), m(0))
    assert active_min(t, m(4)) == 4  # open span counts up to now
    t = pause(t, m(10))
    t = resume(t, m(15))
    t = stop(t, m(25))
    assert active_min(t, m(99)) == 20
    assert wall_min(t) == 25


def test_stop_from_paused_counts_pause_in_wall_only() -> None:
    t = pause(start(mk(Status.READY), m(0)), m(10))
    before = active_min(t, m(40))
    t = stop(t, m(40))
    assert active_min(t, m(40)) == before == 10
    assert wall_min(t) == 40


def test_fractional_minutes() -> None:
    t = stop(start(mk(Status.READY), m(0)), m(0.5))
    assert active_min(t, m(1)) == 0.5


@pytest.mark.parametrize("cmd", ["start", "pause", "resume", "stop"])
def test_naive_datetime_rejected(cmd: str) -> None:
    status = {"start": Status.READY, "resume": Status.PAUSED}.get(cmd, Status.RUNNING)
    with pytest.raises(ValueError):
        COMMANDS[cmd](mk(status), datetime(2026, 1, 1, 12, 30))


def test_naive_at_and_non_utc_rejected() -> None:
    with pytest.raises(ValueError):
        pause(mk(Status.RUNNING), m(10), at=datetime(2026, 1, 1, 12, 5))
    with pytest.raises(ValueError):
        start(mk(Status.READY), datetime(2026, 1, 1, 18, 0, tzinfo=IST))


def test_active_min_naive_now_rejected() -> None:
    with pytest.raises(ValueError):
        active_min(mk(Status.RUNNING), datetime(2026, 1, 1))

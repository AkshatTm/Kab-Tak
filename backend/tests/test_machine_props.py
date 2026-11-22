from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.timer.machine import (
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

T0 = datetime(2026, 1, 1, tzinfo=UTC)

step = st.tuples(
    st.integers(0, 2),  # task index
    st.sampled_from(["start", "pause", "resume", "stop"]),
    st.floats(0, 60),  # minutes the clock advances first
    st.one_of(st.none(), st.floats(-30, 5)),  # at = now + offset (often invalid)
)


def check(tasks: list[Task], now: datetime) -> None:
    assert sum(s.end is None for t in tasks for s in t.sessions) <= 1
    for t in tasks:
        for a, b in zip(t.sessions, t.sessions[1:], strict=False):
            assert a.end is not None and a.start <= a.end <= b.start
        if t.status is Status.STOPPED:
            total = sum((s.end - s.start).total_seconds() / 60 for s in t.sessions if s.end)
            assert active_min(t, now) == pytest.approx(total)
            assert active_min(t, now) <= wall_min(t) + 1e-9


@settings(max_examples=200, deadline=None)
@given(st.lists(step, max_size=40))
def test_invariants(steps: list[tuple[int, str, float, float | None]]) -> None:
    tasks = [Task(Status.READY, 30, ()) for _ in range(3)]
    now = T0
    for i, cmd, advance, off in steps:
        now += timedelta(minutes=advance)
        if cmd in ("start", "resume") and any(t.status is Status.RUNNING for t in tasks):
            continue  # the service's single-running rule
        at = None if off is None else now + timedelta(minutes=off)
        try:
            if cmd == "start":
                tasks[i] = start(tasks[i], now)
            elif cmd == "resume":
                tasks[i] = resume(tasks[i], now)
            elif cmd == "pause":
                tasks[i] = pause(tasks[i], now, at)
            else:
                tasks[i] = stop(tasks[i], now, at)
        except TimerError:
            pass
        check(tasks, now)

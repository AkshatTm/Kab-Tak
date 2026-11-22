import threading
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.db.engine import make_engine
from app.db.models import Event, PartType
from app.db.models import Session as SessionRow
from app.timer.inputs import CompletedPart, PartIn, PauseIn, StopIn, TaskCreate, TaskPatch
from app.timer.machine import InvalidAt, InvalidTransition
from app.timer.service import AlreadyRunning, NotFound, TaskService
from tests.fakeclock import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def engine(migrated_url: str) -> Iterator[Engine]:
    e = make_engine(migrated_url)
    yield e
    e.dispose()


@pytest.fixture
def svc(engine: Engine, clock: FakeClock) -> TaskService:
    return TaskService(engine, clock)


def mk(svc: TaskService, title: str = "t", est: int | None = 60) -> str:
    return svc.create_task(TaskCreate(title=title, estimate_min=est)).task.id


def test_lifecycle_numbers(svc: TaskService, clock: FakeClock) -> None:
    tid = mk(svc)
    assert svc.get_task(tid).task.status == "ready"
    svc.start(tid)
    clock.advance(10)
    svc.pause(tid, PauseIn())
    clock.advance(5)
    svc.resume(tid)
    clock.advance(10)
    done = svc.stop(tid, StopIn(outcome="done")).task
    assert (done.status, done.active_min, done.wall_min, done.outcome) == (
        "stopped",
        20,
        25,
        "done",
    )
    assert done.started_at is not None and done.stopped_at is not None


def test_draft_cannot_start_and_estimate_flips_to_ready(svc: TaskService) -> None:
    tid = mk(svc, est=None)
    assert svc.get_task(tid).task.status == "draft"
    with pytest.raises(InvalidTransition):
        svc.start(tid)
    assert svc.update_task(tid, TaskPatch(estimate_min=30)).task.status == "ready"
    svc.start(tid)


def test_second_start_conflicts(svc: TaskService) -> None:
    a, b = mk(svc, "a"), mk(svc, "b")
    svc.start(a)
    with pytest.raises(AlreadyRunning) as e:
        svc.start(b)
    assert e.value.task_id == a
    svc.pause(a, PauseIn())
    svc.start(b)
    with pytest.raises(AlreadyRunning):
        svc.resume(a)


def test_events_match_transitions(svc: TaskService, clock: FakeClock, engine: Engine) -> None:
    tid = mk(svc)
    svc.start(tid)
    clock.advance(1)
    svc.pause(tid, PauseIn())
    svc.resume(tid)
    svc.stop(tid, StopIn(outcome="partly"))
    with Session(engine) as s:
        types = [e.type for e in s.exec(select(Event))]
    assert sorted(types) == sorted(
        ["task_created", "task_started", "task_paused", "task_resumed", "task_stopped"]
    )


def test_at_validation_and_stop_from_paused(svc: TaskService, clock: FakeClock) -> None:
    tid = mk(svc)
    t0 = clock.now()
    svc.start(tid)
    clock.advance(10)
    with pytest.raises(InvalidAt):
        svc.pause(tid, PauseIn(at=t0 - timedelta(minutes=1)))
    with pytest.raises(InvalidAt):
        svc.pause(tid, PauseIn(at=clock.now() + timedelta(minutes=1)))
    svc.pause(tid, PauseIn(at=t0 + timedelta(minutes=8)))  # forgotten timer: drop the last 2 min
    clock.advance(30)
    done = svc.stop(tid, StopIn(outcome="done")).task
    assert done.active_min == 8 and done.wall_min == 40


def test_parts_and_completed_parts(svc: TaskService, engine: Engine) -> None:
    with Session(engine) as s:
        pt = s.exec(select(PartType)).first()
        assert pt is not None
        pt_id = pt.id
    v = svc.create_task(
        TaskCreate(title="p", estimate_min=30, parts=[PartIn(part_type_id=pt_id, planned_qty=5)])
    )
    svc.start(v.task.id)
    out = svc.stop(
        v.task.id,
        StopIn(
            outcome="partly",
            completed_parts=[CompletedPart(part_id=v.parts[0].id, completed_qty=3)],
        ),
    )
    assert out.parts[0].completed_qty == 3


def test_unknown_part_on_stop_is_rejected_and_task_stays_running(svc: TaskService) -> None:
    tid = mk(svc)
    svc.start(tid)
    with pytest.raises(ValueError):
        svc.stop(
            tid,
            StopIn(
                outcome="done", completed_parts=[CompletedPart(part_id="nope", completed_qty=1)]
            ),
        )
    assert svc.get_task(tid).task.status == "running"


def test_running_and_list_by_study_day(svc: TaskService, clock: FakeClock) -> None:
    assert svc.running_task() is None
    mk(svc, "afternoon")  # 17:30 local, Jan 1
    clock.advance(7 * 60)  # 00:30 local, Jan 2 -> still study day Jan 1
    night = mk(svc, "night")
    svc.start(night)
    running = svc.running_task()
    assert (
        running is not None and running.task.id == night and running.open_session_start is not None
    )
    clock.advance(3.5 * 60)  # 04:00 local -> study day Jan 2
    mk(svc, "morning")
    assert [v.task.title for v in svc.list_tasks(date(2026, 1, 1))] == ["afternoon", "night"]
    assert [v.task.title for v in svc.list_tasks(date(2026, 1, 2))] == ["morning"]
    assert [v.task.title for v in svc.list_tasks(None)] == ["morning"]


def test_unknown_id(svc: TaskService) -> None:
    with pytest.raises(NotFound):
        svc.get_task("nope")


def test_concurrent_start_exactly_one_wins(svc: TaskService) -> None:
    a, b = mk(svc, "a"), mk(svc, "b")
    results: list[str] = []
    barrier = threading.Barrier(2)

    def go(tid: str) -> None:
        barrier.wait()
        try:
            svc.start(tid)
            results.append("ok")
        except AlreadyRunning:
            results.append("conflict")

    threads = [threading.Thread(target=go, args=(t,)) for t in (a, b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["conflict", "ok"]
    with Session(svc.engine) as s:
        open_rows = s.exec(select(SessionRow).where(col(SessionRow.end_at).is_(None))).all()
        assert len(open_rows) == 1

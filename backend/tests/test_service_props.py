import tempfile
from pathlib import Path

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from sqlmodel import Session, select

from app.db.engine import make_engine
from app.db.migrate import upgrade_with_backup
from app.db.models import Session as SessionRow
from app.db.models import Task as TaskRow
from app.timer.inputs import PauseIn, StopIn, TaskCreate
from app.timer.machine import TimerError
from app.timer.service import AlreadyRunning, TaskService
from tests.fakeclock import FakeClock


class ServiceMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.tmp = tempfile.TemporaryDirectory()
        url = f"sqlite:///{(Path(self.tmp.name) / 'p.db').as_posix()}"
        upgrade_with_backup(url)
        self.engine = make_engine(url)
        self.clock = FakeClock()
        self.svc = TaskService(self.engine, self.clock)
        self.ids = [
            self.svc.create_task(TaskCreate(title=f"t{i}", estimate_min=30)).task.id
            for i in range(3)
        ]

    def teardown(self) -> None:
        self.engine.dispose()
        self.tmp.cleanup()

    @rule(minutes=st.integers(min_value=0, max_value=90))
    def tick(self, minutes: int) -> None:
        self.clock.advance(minutes)

    @rule(i=st.integers(0, 2), cmd=st.sampled_from(["start", "pause", "resume", "stop"]))
    def command(self, i: int, cmd: str) -> None:
        tid = self.ids[i]
        try:
            if cmd == "start":
                self.svc.start(tid)
            elif cmd == "resume":
                self.svc.resume(tid)
            elif cmd == "pause":
                self.svc.pause(tid, PauseIn())
            else:
                self.svc.stop(tid, StopIn(outcome="done"))
        except (TimerError, AlreadyRunning):
            pass  # rejected commands must leave the data untouched; the invariants check that

    @invariant()
    def never_two_running_and_sessions_consistent(self) -> None:
        with Session(self.engine) as s:
            running = s.exec(select(TaskRow).where(TaskRow.status == "running")).all()
            open_rows = [r for r in s.exec(select(SessionRow)).all() if r.end_at is None]
            assert len(running) <= 1
            assert len(open_rows) == len(running)
            for tid in self.ids:
                rows = sorted(
                    (r for r in s.exec(select(SessionRow).where(SessionRow.task_id == tid)).all()),
                    key=lambda r: r.start_at,
                )
                for a, b in zip(rows, rows[1:], strict=False):
                    assert a.end_at is not None and a.end_at <= b.start_at
            for t in s.exec(select(TaskRow).where(TaskRow.status == "stopped")).all():
                assert t.active_min is not None and t.wall_min is not None
                assert t.active_min <= t.wall_min + 1e-9


TestServiceMachine = ServiceMachine.TestCase
TestServiceMachine.settings = settings(max_examples=25, stateful_step_count=25, deadline=None)

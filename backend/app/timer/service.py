"""Task + timer service: loads rows, runs the pure state machine, persists, writes events."""

import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.db.models import Category, Event, PartType, Setting, TaskPart
from app.db.models import Session as SessionRow
from app.db.models import Task as TaskRow
from app.db.session import session_scope
from app.timer import machine
from app.timer.clock import Clock
from app.timer.inputs import PartIn, PauseIn, StopIn, TaskCreate, TaskPatch
from app.timer.machine import Span, Status
from app.timer.studyday import parse_cutoff, study_day

# shortcut: one lock = one process. The sidecar is a single process; use a DB-level guard if the
# backend ever runs with several workers.
_LOCK = threading.Lock()
_EVENT = {
    "start": "task_started",
    "pause": "task_paused",
    "resume": "task_resumed",
    "stop": "task_stopped",
}


class NotFound(Exception):
    pass


class BadInput(ValueError):
    pass


class AlreadyRunning(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"task {task_id} is already running")
        self.task_id = task_id


@dataclass
class TaskView:
    task: TaskRow
    parts: list[TaskPart]
    open_session_start: datetime | None


def _aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        raise BadInput("`at` must include a timezone")
    return dt.astimezone(UTC)


class TaskService:
    def __init__(self, engine: Engine, clock: Clock) -> None:
        self.engine = engine
        self.clock = clock

    # ---- reads -------------------------------------------------------------------------------
    def get_task(self, task_id: str) -> TaskView:
        with session_scope(self.engine) as s:
            return self._view(s, self._row(s, task_id))

    def running_task(self) -> TaskView | None:
        with session_scope(self.engine) as s:
            row = s.exec(select(TaskRow).where(TaskRow.status == Status.RUNNING.value)).first()
            return self._view(s, row) if row else None

    def list_tasks(self, day: date | None) -> list[TaskView]:
        # shortcut: filters in Python; fine for one person's history, push into SQL if it gets slow.
        with session_scope(self.engine) as s:
            cutoff = parse_cutoff(self._setting(s, "day_starts_at", "04:00"))
            target = day or study_day(self.clock.now(), self.clock.tz, cutoff)
            rows = s.exec(select(TaskRow).order_by(col(TaskRow.created_at))).all()
            keep = [
                r
                for r in rows
                if study_day(r.started_at or r.created_at, self.clock.tz, cutoff) == target
            ]
            return [self._view(s, r) for r in keep]

    def categories(self) -> list[Category]:
        with session_scope(self.engine) as s:
            return list(s.exec(select(Category).order_by(col(Category.name))).all())

    def part_types(self) -> list[PartType]:
        with session_scope(self.engine) as s:
            return list(s.exec(select(PartType).order_by(col(PartType.key))).all())

    # ---- writes ------------------------------------------------------------------------------
    def create_task(self, data: TaskCreate) -> TaskView:
        now = self.clock.now()
        with session_scope(self.engine) as s:
            row = TaskRow(
                title=data.title,
                raw_text=data.raw_text,
                category_id=data.category_id,
                estimate_min=data.estimate_min,
                status=(Status.READY if data.estimate_min else Status.DRAFT).value,
                tentative=data.tentative,
                familiarity=data.familiarity,
                source=data.source,
                created_at=now,
            )
            s.add(row)
            s.flush()  # no relationship() links, so insert the parent before children (FK order)
            self._set_parts(s, row.id, data.parts)
            self._event(s, row.id, "task_created", now, {})
            s.flush()
            return self._view(s, row)

    def update_task(self, task_id: str, data: TaskPatch) -> TaskView:
        now = self.clock.now()
        with session_scope(self.engine) as s:
            row = self._row(s, task_id)
            sent = data.model_dump(exclude_unset=True, exclude={"parts"})
            for key, value in sent.items():
                if key == "estimate_min" and value is None:
                    continue  # can be set, not cleared
                setattr(row, key, value)
            if row.status == Status.DRAFT.value and row.estimate_min:
                row.status = Status.READY.value
            if data.parts is not None:
                self._set_parts(s, row.id, data.parts, replace=True)
            self._event(s, row.id, "task_updated", now, {"fields": sorted(sent)})
            s.flush()
            return self._view(s, row)

    def start(self, task_id: str) -> TaskView:
        return self._run(task_id, "start", None)

    def resume(self, task_id: str) -> TaskView:
        return self._run(task_id, "resume", None)

    def pause(self, task_id: str, body: PauseIn) -> TaskView:
        return self._run(task_id, "pause", _aware_utc(body.at))

    def stop(self, task_id: str, body: StopIn) -> TaskView:
        return self._run(task_id, "stop", _aware_utc(body.at), body)

    # ---- internals ---------------------------------------------------------------------------
    def _run(
        self, task_id: str, cmd: str, at: datetime | None, stop_body: StopIn | None = None
    ) -> TaskView:
        now = self.clock.now()
        with _LOCK, session_scope(self.engine) as s:  # lock covers check + write + commit (D6)
            row = self._row(s, task_id)
            old = self._to_machine(s, row)
            if cmd in ("start", "resume"):
                other = s.exec(
                    select(TaskRow).where(
                        TaskRow.status == Status.RUNNING.value, TaskRow.id != task_id
                    )
                ).first()
                if other:
                    raise AlreadyRunning(other.id)
            if stop_body:
                self._check_parts(s, task_id, stop_body)
            new = (
                machine.start(old, now)
                if cmd == "start"
                else machine.resume(old, now)
                if cmd == "resume"
                else machine.pause(old, now, at)
                if cmd == "pause"
                else machine.stop(old, now, at)
            )
            self._persist(s, row, old, new, cmd)
            if cmd == "stop":
                row.active_min = machine.active_min(new, now)
                row.wall_min = machine.wall_min(new)
                assert stop_body is not None
                row.outcome = stop_body.outcome
                for cp in stop_body.completed_parts:
                    part = s.get(TaskPart, cp.part_id)
                    assert part is not None  # checked above
                    part.completed_qty = cp.completed_qty
            self._event(s, row.id, _EVENT[cmd], now, {"at": (at or now).isoformat()})
            s.flush()
            return self._view(s, row)

    @staticmethod
    def _row(s: Session, task_id: str) -> TaskRow:
        row = s.get(TaskRow, task_id)
        if row is None:
            raise NotFound(task_id)
        return row

    @staticmethod
    def _setting(s: Session, key: str, default: str) -> str:
        row = s.get(Setting, key)
        return str(row.value_json) if row else default

    @staticmethod
    def _sessions(s: Session, task_id: str) -> list[SessionRow]:
        return list(
            s.exec(
                select(SessionRow)
                .where(SessionRow.task_id == task_id)
                .order_by(col(SessionRow.start_at))
            ).all()
        )

    def _to_machine(self, s: Session, row: TaskRow) -> machine.Task:
        spans = tuple(Span(r.start_at, r.end_at) for r in self._sessions(s, row.id))
        return machine.Task(Status(row.status), row.estimate_min, spans, row.stopped_at)

    def _persist(
        self, s: Session, row: TaskRow, old: machine.Task, new: machine.Task, cmd: str
    ) -> None:
        rows = self._sessions(s, row.id)
        if len(new.sessions) > len(old.sessions):
            s.add(SessionRow(task_id=row.id, start_at=new.sessions[-1].start))
        elif rows and new.sessions[-1].end != old.sessions[-1].end:
            rows[-1].end_at = new.sessions[-1].end
            rows[-1].end_reason = "pause" if cmd == "pause" else "stop"
        row.status = new.status.value
        row.stopped_at = new.stopped_at
        row.started_at = new.sessions[0].start if new.sessions else None

    @staticmethod
    def _check_parts(s: Session, task_id: str, body: StopIn) -> None:
        for cp in body.completed_parts:
            part = s.get(TaskPart, cp.part_id)
            if part is None or part.task_id != task_id:
                raise BadInput(f"unknown part {cp.part_id} for this task")

    @staticmethod
    def _set_parts(s: Session, task_id: str, parts: list[PartIn], replace: bool = False) -> None:
        if replace:
            for old in s.exec(select(TaskPart).where(TaskPart.task_id == task_id)).all():
                s.delete(old)
        for i, p in enumerate(parts):
            s.add(
                TaskPart(
                    task_id=task_id, part_type_id=p.part_type_id, planned_qty=p.planned_qty, order=i
                )
            )

    @staticmethod
    def _event(
        s: Session, task_id: str, type_: str, now: datetime, payload: dict[str, Any]
    ) -> None:
        s.add(Event(task_id=task_id, type=type_, payload_json=payload, created_at=now))

    def _view(self, s: Session, row: TaskRow) -> TaskView:
        s.flush()
        parts = list(
            s.exec(
                select(TaskPart).where(TaskPart.task_id == row.id).order_by(col(TaskPart.order))
            ).all()
        )
        open_row = next((r for r in reversed(self._sessions(s, row.id)) if r.end_at is None), None)
        return TaskView(row, parts, open_row.start_at if open_row else None)

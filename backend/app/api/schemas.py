"""Response models. Request bodies live in app.timer.inputs."""

from datetime import datetime

from pydantic import BaseModel

from app.timer.service import TaskView


class PartOut(BaseModel):
    id: str
    part_type_id: str
    planned_qty: float
    completed_qty: float | None
    order: int


class TaskOut(BaseModel):
    id: str
    title: str
    raw_text: str | None
    category_id: str | None
    estimate_min: int | None
    status: str
    outcome: str | None
    tentative: bool
    familiarity: str | None
    source: str
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    active_min: float | None
    wall_min: float | None
    parts: list[PartOut]
    open_session_start: datetime | None  # D5: the UI adds its own clock to this

    @classmethod
    def of(cls, v: TaskView) -> "TaskOut":
        t = v.task
        return cls(
            **t.model_dump(),
            parts=[PartOut(**p.model_dump()) for p in v.parts],
            open_session_start=v.open_session_start,
        )


class ErrorOut(BaseModel):
    detail: str


class ConflictOut(BaseModel):
    detail: str
    running_task_id: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    parent_id: str | None


class PartTypeOut(BaseModel):
    id: str
    key: str
    unit: str
    label: str

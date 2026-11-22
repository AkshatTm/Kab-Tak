from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel

from app.db.types import UTCDateTime


def _id() -> str:
    return str(uuid4())


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: str = Field(default_factory=_id, primary_key=True)
    name: str = Field(unique=True)
    parent_id: str | None = Field(default=None, foreign_key="categories.id")
    created_at: datetime = Field(sa_type=UTCDateTime)


class PartType(SQLModel, table=True):
    __tablename__ = "part_types"
    id: str = Field(default_factory=_id, primary_key=True)
    key: str = Field(unique=True)
    unit: str
    label: str


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: str = Field(default_factory=_id, primary_key=True)
    title: str
    raw_text: str | None = None
    category_id: str | None = Field(default=None, foreign_key="categories.id")
    estimate_min: int | None = None
    status: str  # Status
    outcome: str | None = None  # Outcome
    tentative: bool = False
    familiarity: str | None = None  # Familiarity
    source: str  # Source
    created_at: datetime = Field(sa_type=UTCDateTime)
    started_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    stopped_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    active_min: float | None = None
    wall_min: float | None = None


class TaskPart(SQLModel, table=True):
    __tablename__ = "task_parts"
    id: str = Field(default_factory=_id, primary_key=True)
    task_id: str = Field(foreign_key="tasks.id")
    part_type_id: str = Field(foreign_key="part_types.id")
    planned_qty: float
    completed_qty: float | None = None
    order: int = 0


class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    id: str = Field(default_factory=_id, primary_key=True)
    task_id: str = Field(foreign_key="tasks.id")
    start_at: datetime = Field(sa_type=UTCDateTime)
    end_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    end_reason: str | None = None  # EndReason


class Prediction(SQLModel, table=True):
    __tablename__ = "predictions"
    id: str = Field(default_factory=_id, primary_key=True)
    task_id: str = Field(foreign_key="tasks.id")
    model_level: str  # ModelLevel
    model_version: str
    point_min: float
    low_min: float
    high_min: float
    shown: bool = False
    created_at: datetime = Field(sa_type=UTCDateTime)


class Correction(SQLModel, table=True):
    __tablename__ = "corrections"
    id: str = Field(default_factory=_id, primary_key=True)
    raw_text: str
    llm_output_json: Any = Field(sa_type=JSON)
    corrected_json: Any = Field(sa_type=JSON)
    created_at: datetime = Field(sa_type=UTCDateTime)


class LlmCall(SQLModel, table=True):
    __tablename__ = "llm_calls"
    id: str = Field(default_factory=_id, primary_key=True)
    provider: str
    model: str
    latency_ms: int
    ok: bool
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    created_at: datetime = Field(sa_type=UTCDateTime)


class Setting(SQLModel, table=True):
    __tablename__ = "settings"
    key: str = Field(primary_key=True)
    value_json: Any = Field(sa_type=JSON)


class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: str = Field(default_factory=_id, primary_key=True)
    task_id: str | None = Field(default=None, foreign_key="tasks.id")
    type: str
    payload_json: Any = Field(default=None, sa_type=JSON, nullable=True)
    created_at: datetime = Field(sa_type=UTCDateTime)

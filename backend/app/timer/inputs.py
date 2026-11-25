"""Request bodies. Shared by the service and the API (Pydantic for all API I/O)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MAX_ESTIMATE_MIN = 10_000  # about a week; anything larger is a typo or a bad parse
MAX_QTY = 100_000


class PartIn(BaseModel):
    part_type_id: str
    planned_qty: float = Field(gt=0, le=MAX_QTY, allow_inf_nan=False)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    raw_text: str | None = None
    category_id: str | None = None
    estimate_min: int | None = Field(default=None, gt=0, le=MAX_ESTIMATE_MIN)
    tentative: bool = False
    familiarity: Literal["new", "familiar"] | None = None
    source: Literal["chat", "retro", "manual"] = "manual"
    parts: list[PartIn] = []


class TaskPatch(BaseModel):
    """Only fields that are sent change. `estimate_min` can be set but not cleared."""

    title: str | None = Field(default=None, min_length=1)
    raw_text: str | None = None
    category_id: str | None = None
    estimate_min: int | None = Field(default=None, gt=0, le=MAX_ESTIMATE_MIN)
    tentative: bool | None = None
    familiarity: Literal["new", "familiar"] | None = None
    parts: list[PartIn] | None = None


class PauseIn(BaseModel):
    at: datetime | None = None


class CompletedPart(BaseModel):
    part_id: str
    completed_qty: float = Field(ge=0, le=MAX_QTY, allow_inf_nan=False)


class StopIn(BaseModel):
    outcome: Literal["done", "partly", "stuck"]
    completed_parts: list[CompletedPart] = []
    at: datetime | None = None

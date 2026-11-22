"""Request bodies. Shared by the service and the API (Pydantic for all API I/O)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PartIn(BaseModel):
    part_type_id: str
    planned_qty: float = Field(gt=0)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    raw_text: str | None = None
    category_id: str | None = None
    estimate_min: int | None = Field(default=None, gt=0)
    tentative: bool = False
    familiarity: Literal["new", "familiar"] | None = None
    source: Literal["chat", "retro", "manual"] = "manual"
    parts: list[PartIn] = []


class TaskPatch(BaseModel):
    """Only fields that are sent change. `estimate_min` can be set but not cleared."""

    title: str | None = Field(default=None, min_length=1)
    raw_text: str | None = None
    category_id: str | None = None
    estimate_min: int | None = Field(default=None, gt=0)
    tentative: bool | None = None
    familiarity: Literal["new", "familiar"] | None = None
    parts: list[PartIn] | None = None


class PauseIn(BaseModel):
    at: datetime | None = None


class CompletedPart(BaseModel):
    part_id: str
    completed_qty: float = Field(ge=0)


class StopIn(BaseModel):
    outcome: Literal["done", "partly", "stuck"]
    completed_parts: list[CompletedPart] = []
    at: datetime | None = None

"""LLM parse schema (SPEC §3.2)."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.timer.inputs import MAX_ESTIMATE_MIN, MAX_QTY

Intent = Literal[
    "create_task",
    "update_task",
    "stop_with_outcome",
    "retro_log",
    "plan_check",
    "question",
    "unknown",
]


class _LlmModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _null_means_default(cls, data: Any) -> Any:
        # LLMs send null for empty lists and bools; a required field still fails when dropped.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class ParsedPart(_LlmModel):
    type: str
    quantity: float = Field(gt=0, le=MAX_QTY, allow_inf_nan=False)
    unit: str | None = None


class ParsedTask(_LlmModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    category: str | None = None
    estimate_min: int | None = Field(default=None, gt=0, le=MAX_ESTIMATE_MIN)
    familiarity: Literal["new", "familiar"] | None = None
    tentative: bool = False
    parts: list[ParsedPart] = []


class ParseResult(_LlmModel):
    intent: Intent
    task: ParsedTask | None = None
    extra_tasks: list[ParsedTask] = []
    confidence: float = 0.0
    clarifying_question: str | None = None

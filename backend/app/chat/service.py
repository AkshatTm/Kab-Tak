"""Chat text -> task cards (SPEC §2.3, §2.4). Nothing is persisted here."""

import json
import re
from collections.abc import Sequence
from importlib.resources import files
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import col, select

from app.chat.schema import ParsedTask, ParseResult
from app.db.models import Category, Correction, PartType
from app.db.session import session_scope
from app.timer.inputs import PartIn, TaskCreate

T = TypeVar("T", bound=BaseModel)

_FEW_SHOT = 10
_TITLE_MAX = 120
_FAILED = "Couldn't understand that — fill the card manually"

# shortcut: ADR 0004 heuristic (any digit, number word or time word lets the LLM's estimate
# through, even "2 problems"); tighten or extend if the eval shows invented or false-null values.
# Hinglish numbers (ek, do, teen) are left out on purpose: they only mean a duration next to a
# time word, which already matches, and "do" is also an English verb.
_HAS_TIME_HINT = re.compile(
    r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty"
    r"|thirty|forty|fifty|sixty|ninety|half|quarter|couple"
    r"|minutes?|mins?|minat|hours?|hrs?|ghant[ae]|ghanton)\b",
    re.IGNORECASE,
)


class Completer(Protocol):
    def complete_json(self, messages: list[dict[str, str]], schema: type[T]) -> T | None: ...


class ChatResponse(BaseModel):
    intent: str
    reply: str
    cards: list[TaskCreate]
    parsed: bool
    parse_json: dict[str, Any] | None


class ChatService:
    def __init__(self, engine: Engine, completer: Completer) -> None:
        self.engine = engine
        self.completer = completer

    def parse(self, text: str) -> ChatResponse:
        with session_scope(self.engine) as s:
            categories = s.exec(select(Category).order_by(Category.name)).all()
            part_types = s.exec(select(PartType).order_by(PartType.key)).all()
            corrections = s.exec(
                select(Correction).order_by(col(Correction.created_at).desc()).limit(_FEW_SHOT)
            ).all()
        messages = [
            {"role": "system", "content": _system_prompt(categories, part_types, corrections)},
            {"role": "user", "content": text},
        ]

        result = self.completer.complete_json(messages, ParseResult)
        if result is None:
            return self._failed(text)

        tasks = [t for t in [result.task, *result.extra_tasks] if t is not None]
        if not _HAS_TIME_HINT.search(text):
            for task in tasks:
                task.estimate_min = None

        intent: str = result.intent
        if intent == "create_task" and result.task is None:
            intent = "unknown"

        cards: list[TaskCreate] = []
        if intent == "create_task":
            category_ids = {c.name.casefold(): c.id for c in categories}
            part_ids = {p.key.casefold(): p.id for p in part_types}
            cards = [_card(t, text, category_ids, part_ids) for t in tasks]
            reply = result.clarifying_question or "Check the card, then confirm."
        elif intent in ("question", "unknown"):
            reply = result.clarifying_question or "Tell me the task you want to work on."
        else:
            reply = "That isn't available yet."

        return ChatResponse(
            intent=intent, reply=reply, cards=cards, parsed=True, parse_json=result.model_dump()
        )

    def _failed(self, text: str) -> ChatResponse:
        reply = _FAILED
        has_any_key = getattr(self.completer, "has_any_key", None)
        if has_any_key is not None and not has_any_key():
            reply += " (no API key is configured)"
        title = " ".join(text.split())[:_TITLE_MAX].rstrip() or "Untitled task"
        card = TaskCreate(title=title, raw_text=text, source="chat")
        return ChatResponse(
            intent="unknown", reply=reply, cards=[card], parsed=False, parse_json=None
        )


def _system_prompt(
    categories: Sequence[Category],
    part_types: Sequence[PartType],
    corrections: Sequence[Correction],
) -> str:
    template = files("app.chat").joinpath("prompts", "parse_task.md").read_text(encoding="utf-8")
    prompt = template.replace("{{categories}}", "\n".join(f"- {c.name}" for c in categories))
    prompt = prompt.replace(
        "{{part_types}}", "\n".join(f"- {p.key} ({p.unit})" for p in part_types)
    )
    if not corrections:
        return prompt
    # In the system prompt, not as assistant turns: a corrected card is not the output schema.
    examples = "\n\n".join(
        f"Input: {json.dumps(c.raw_text, ensure_ascii=False)}\n"
        f"Corrected: {json.dumps(c.corrected_json, ensure_ascii=False)}"
        for c in corrections
    )
    return (
        f"{prompt}\n## The user's own fixes, newest first\n"
        "Learn the preferred values from these. Always answer in the output schema above.\n\n"
        f"{examples}\n"
    )


def _card(
    task: ParsedTask, text: str, category_ids: dict[str, str], part_ids: dict[str, str]
) -> TaskCreate:
    return TaskCreate(
        title=task.title,
        raw_text=text,
        category_id=category_ids.get((task.category or "").strip().casefold()),
        estimate_min=task.estimate_min,
        tentative=task.tentative,
        familiarity=task.familiarity,
        source="chat",
        parts=[
            PartIn(
                part_type_id=part_ids.get(p.type.strip().casefold(), part_ids["other"]),
                planned_qty=p.quantity,
            )
            for p in task.parts
        ],
    )

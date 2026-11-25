"""Live parser eval: `uv run pytest -m live tests/test_chat_eval.py -s`. Fails below 90% overall."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, PositiveFloat, PositiveInt

pytestmark = pytest.mark.live

FIXTURE = Path(__file__).parent / "fixtures" / "chat_eval.jsonl"
FIELDS = ("intent", "n_tasks", "category", "estimate_min", "tentative", "familiarity", "parts")
THRESHOLD = 0.90


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoldPart(Strict):
    type: str
    quantity: PositiveFloat


class GoldTask(Strict):
    category: str | None
    estimate_min: PositiveInt | None
    tentative: bool
    familiarity: Literal["new", "familiar"] | None
    parts: list[GoldPart]


class GoldLine(Strict):
    text: str
    intent: Literal["create_task", "question", "unknown"]
    tasks: list[GoldTask]
    lang: Literal["hinglish"] | None = None


def load_gold() -> list[GoldLine]:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    return [GoldLine.model_validate_json(line) for line in lines if line.strip()]


@dataclass
class Report:
    correct: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    total: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    mismatches: list[str] = field(default_factory=list)

    @property
    def overall(self) -> float:
        return sum(self.correct.values()) / max(sum(self.total.values()), 1)

    def add(self, name: str, text: str, want: object, got: object, ok: bool) -> None:
        self.total[name] += 1
        self.correct[name] += ok
        if not ok:
            self.mismatches.append(f"{text!r} [{name}] want {want!r}, got {got!r}")

    def table(self) -> str:
        rows = [(n, self.correct[n], self.total[n]) for n in FIELDS]
        rows.append(("overall", sum(self.correct.values()), sum(self.total.values())))
        return "\n".join(f"{n:<13} {c:>3}/{t:<3} {c / max(t, 1):6.1%}" for n, c, t in rows)


def _comparable(name: str, value: Any) -> Any:
    if name == "parts":
        return {(p["type"], float(p["quantity"])) for p in value or []}
    if name == "category" and isinstance(value, str):
        return value.casefold()
    return value


def score(cases: list[tuple[GoldLine, dict[str, Any] | None]]) -> Report:
    """Score (gold, parse_json) pairs per field; None means the parse failed."""
    report = Report()
    for gold, parsed in cases:
        intent, tasks = None, []
        if parsed is not None:
            intent = parsed.get("intent")
            tasks = [t for t in [parsed.get("task"), *(parsed.get("extra_tasks") or [])] if t]
            # A question/unknown reply makes no card, so a stray task object there is ignored.
            if intent in ("question", "unknown"):
                tasks = []
        n_tasks = None if parsed is None else len(tasks)
        report.add("intent", gold.text, gold.intent, intent, intent == gold.intent)
        report.add("n_tasks", gold.text, len(gold.tasks), n_tasks, n_tasks == len(gold.tasks))
        for i, want_task in enumerate(gold.tasks):
            want = want_task.model_dump()
            got = tasks[i] if i < len(tasks) else None
            for name in FIELDS[2:]:
                value = None if got is None else got.get(name)
                ok = got is not None and _comparable(name, value) == _comparable(name, want[name])
                shown = "<missing task>" if got is None else value
                report.add(name, f"{gold.text} #{i + 1}", want[name], shown, ok)
    return report


def test_live_chat_eval(migrated_url: str) -> None:
    # Imported here so the fixture/scorer tests run without the LLM stack.
    from app.chat.service import ChatService
    from app.db.engine import make_engine
    from app.llm.chain import LlmChain
    from app.llm.config import ProviderKeys, load_config

    engine = make_engine(migrated_url)
    chain = LlmChain(load_config(), ProviderKeys(), engine)
    if not chain.has_any_key():
        pytest.skip("no LLM key: set GROQ_API_KEY, CEREBRAS_API_KEY or GEMINI_API_KEY in .env")
    service = ChatService(engine, chain)

    cases: list[tuple[GoldLine, dict[str, Any] | None]] = []
    for gold in load_gold():
        response = service.parse(gold.text)
        parsed = response.parse_json if response.parsed else None
        if isinstance(parsed, BaseModel):
            parsed = parsed.model_dump(mode="json")
        cases.append((gold, parsed))

    report = score(cases)
    print("\n" + report.table())
    print("\n".join(["", f"{len(report.mismatches)} mismatches:", *report.mismatches]))
    assert report.overall >= THRESHOLD, f"overall {report.overall:.1%} < {THRESHOLD:.0%}"

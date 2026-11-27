from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import Engine
from sqlmodel import select

from app.chat.schema import ParsedPart, ParsedTask, ParseResult
from app.chat.service import ChatService
from app.db.engine import make_engine
from app.db.models import Category, Correction, PartType
from app.db.session import session_scope

T = TypeVar("T", bound=BaseModel)

VIDEO = "Backtracking Video 2 finish + 2 problems, I think 90 min"
FALLBACK = "Couldn't understand that — fill the card manually"


class FakeCompleter:
    def __init__(self, result: ParseResult | None) -> None:
        self.result = result
        self.messages: list[dict[str, str]] = []

    def complete_json(self, messages: list[dict[str, str]], schema: type[T]) -> T | None:
        self.messages = messages
        return None if self.result is None else schema.model_validate(self.result.model_dump())


class KeylessCompleter(FakeCompleter):
    def has_any_key(self) -> bool:
        return False


@pytest.fixture
def engine(migrated_url: str) -> Iterator[Engine]:
    eng = make_engine(migrated_url)
    yield eng
    eng.dispose()


def one_task(**kwargs: Any) -> ParseResult:
    return ParseResult(intent="create_task", task=ParsedTask(**{"title": "T", **kwargs}))


def ids(engine: Engine) -> tuple[dict[str, str], dict[str, str]]:
    with session_scope(engine) as s:
        return (
            {c.name: c.id for c in s.exec(select(Category))},
            {p.key: p.id for p in s.exec(select(PartType))},
        )


# --- schema ---


def test_schema_tolerates_nulls_for_lists_bools_and_confidence() -> None:
    result = ParseResult.model_validate(
        {
            "intent": "create_task",
            "task": {"title": "x", "parts": None, "tentative": None},
            "extra_tasks": None,
            "confidence": None,
        }
    )
    assert result.extra_tasks == [] and result.confidence == 0.0
    assert result.task is not None
    assert result.task.parts == [] and result.task.tentative is False


@pytest.mark.parametrize(
    "data",
    [
        {"intent": "predict"},
        {"intent": None},
        {"intent": "create_task", "task": {"title": "  "}},
        {"intent": "create_task", "task": {"title": "x", "estimate_min": 0}},
        {
            "intent": "create_task",
            "task": {"title": "x", "parts": [{"type": "notes", "quantity": 0}]},
        },
    ],
)
def test_schema_rejects_bad_output(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ParseResult.model_validate(data)


# --- cards ---


def test_video_sentence_becomes_one_card_with_ids(engine: Engine) -> None:
    categories, parts = ids(engine)
    result = one_task(
        title="Backtracking – Video 2 finish + 2 problems",
        category="dsa",
        estimate_min=90,
        familiarity="new",
        parts=[
            ParsedPart(type="video_watch", quantity=30, unit="content_min"),
            ParsedPart(type="Handwrite_Code", quantity=2, unit="problems"),
            ParsedPart(type="implement_code", quantity=2),
        ],
    )
    response = ChatService(engine, FakeCompleter(result)).parse(VIDEO)

    assert response.intent == "create_task" and response.parsed and response.reply
    [card] = response.cards
    assert card.title == "Backtracking – Video 2 finish + 2 problems"
    assert card.category_id == categories["DSA"]
    assert card.estimate_min == 90 and card.familiarity == "new"
    assert card.source == "chat" and card.raw_text == VIDEO
    assert [(p.part_type_id, p.planned_qty) for p in card.parts] == [
        (parts["video_watch"], 30),
        (parts["handwrite_code"], 2),
        (parts["implement_code"], 2),
    ]
    assert response.parse_json == result.model_dump()


def test_unknown_category_and_part_type(engine: Engine) -> None:
    _, parts = ids(engine)
    result = one_task(category="Gardening", parts=[ParsedPart(type="juggling", quantity=3)])
    [card] = ChatService(engine, FakeCompleter(result)).parse("juggle 3 balls").cards
    assert card.category_id is None
    assert card.parts[0].part_type_id == parts["other"]


def test_extra_tasks_become_extra_cards_keeping_tentative(engine: Engine) -> None:
    result = one_task(title="A", estimate_min=30)
    result.extra_tasks = [ParsedTask(title="B", tentative=True, estimate_min=20)]
    cards = ChatService(engine, FakeCompleter(result)).parse("A 30 min, maybe B 20 min").cards
    assert [(c.title, c.tentative, c.estimate_min) for c in cards] == [
        ("A", False, 30),
        ("B", True, 20),
    ]


# --- ADR 0004 guard ---


@pytest.mark.parametrize(
    "text",
    [
        "finish the backtracking video",
        "do my homework",
        "DBMS ka assignment karna hai",
        "kal ke notes banane hain",
        "ek video dekhna hai",
        "mujhe project pe kaam karna hai",
        "do the second assignment today",
    ],
)
def test_guard_nulls_invented_estimates(engine: Engine, text: str) -> None:
    result = one_task(estimate_min=45)
    result.extra_tasks = [ParsedTask(title="B", estimate_min=15)]
    response = ChatService(engine, FakeCompleter(result)).parse(text)
    assert [c.estimate_min for c in response.cards] == [None, None]
    assert response.parse_json is not None
    assert response.parse_json["task"]["estimate_min"] is None
    assert response.parse_json["extra_tasks"][0]["estimate_min"] is None


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        (VIDEO, 90),
        ("DBMS assignment, 1.5 hours", 90),
        ("DBMS assignment ek ghanta", 60),
        ("notes do ghante lagenge", 120),
        ("revision, half an hour", 30),
        ("OS padhna hai, aadha ghanta", 30),
        ("admin stuff, twenty", 20),
        ("graphs 45m", 45),
        ("fix the bug in a couple of hrs", 120),
        ("das minute ka kaam", 10),
    ],
)
def test_guard_keeps_estimates_from_the_users_words(
    engine: Engine, text: str, minutes: int
) -> None:
    service = ChatService(engine, FakeCompleter(one_task(estimate_min=minutes)))
    assert service.parse(text).cards[0].estimate_min == minutes


# --- intents ---


@pytest.mark.parametrize("intent", ["question", "unknown"])
def test_question_and_unknown_reply_without_cards(engine: Engine, intent: str) -> None:
    asked = ParseResult.model_validate({"intent": intent, "clarifying_question": "Which one?"})
    response = ChatService(engine, FakeCompleter(asked)).parse("hmm")
    assert (response.intent, response.reply, response.cards) == (intent, "Which one?", [])
    assert response.parsed

    silent = ParseResult.model_validate({"intent": intent})
    assert ChatService(engine, FakeCompleter(silent)).parse("hmm").reply


@pytest.mark.parametrize("intent", ["update_task", "stop_with_outcome", "retro_log", "plan_check"])
def test_unsupported_intents_are_not_available_yet(engine: Engine, intent: str) -> None:
    result = ParseResult.model_validate({"intent": intent, "task": {"title": "x"}})
    response = ChatService(engine, FakeCompleter(result)).parse("something")
    assert response.intent == intent
    assert response.reply == "That isn't available yet."
    assert response.cards == []


def test_create_task_without_a_task_is_unknown(engine: Engine) -> None:
    result = ParseResult(intent="create_task")
    response = ChatService(engine, FakeCompleter(result)).parse("hmm")
    assert response.intent == "unknown" and response.cards == [] and response.reply


# --- failure ---


def test_completer_failure_gives_a_manual_card(engine: Engine) -> None:
    response = ChatService(engine, FakeCompleter(None)).parse("  read chapter 4  ")
    assert (response.intent, response.parsed, response.parse_json) == ("unknown", False, None)
    assert response.reply == FALLBACK
    [card] = response.cards
    assert card.title == "read chapter 4" and card.raw_text == "  read chapter 4  "
    assert card.source == "chat" and card.estimate_min is None and card.parts == []


@pytest.mark.parametrize("text", ["word " * 200, "   "])
def test_manual_card_title_is_short_and_non_empty(engine: Engine, text: str) -> None:
    [card] = ChatService(engine, FakeCompleter(None)).parse(text).cards
    assert 0 < len(card.title) <= 120


def test_failure_without_any_key_says_so(engine: Engine) -> None:
    reply = ChatService(engine, KeylessCompleter(None)).parse("x").reply
    assert reply.startswith(FALLBACK) and "no API key is configured" in reply


# --- prompt ---


def test_prompt_carries_rules_schema_and_lists(engine: Engine) -> None:
    completer = FakeCompleter(ParseResult(intent="unknown"))
    ChatService(engine, completer).parse("hello")
    system, user = completer.messages
    assert (system["role"], user) == ("system", {"role": "user", "content": "hello"})
    prompt = system["content"]
    assert "Never invent or suggest a duration" in prompt
    assert "JSON" in prompt
    for name in ids(engine)[0]:
        assert name in prompt
    assert "video_watch (content_min)" in prompt and "other (items)" in prompt
    for field in ("extra_tasks", "estimate_min", "clarifying_question", "plan_check", "shayad"):
        assert field in prompt
    assert "{{" not in prompt


def test_few_shot_is_the_latest_ten_corrections_newest_first(engine: Engine) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    with session_scope(engine) as s:
        for i in range(12):
            s.add(
                Correction(
                    raw_text=f"raw-{i:02}",
                    llm_output_json={"title": "wrong"},
                    corrected_json={"title": f"fixed-{i:02}"},
                    created_at=base + timedelta(minutes=i),
                )
            )
    completer = FakeCompleter(ParseResult(intent="unknown"))
    ChatService(engine, completer).parse("hello")
    prompt = completer.messages[0]["content"]
    positions = [prompt.index(f'Input: "raw-{i:02}"') for i in range(11, 1, -1)]
    assert positions == sorted(positions)  # newest first
    assert all(f'"title": "fixed-{i:02}"' in prompt for i in range(2, 12))
    assert "raw-01" not in prompt and "raw-00" not in prompt and "wrong" not in prompt


def test_no_few_shot_block_without_corrections(engine: Engine) -> None:
    completer = FakeCompleter(ParseResult(intent="unknown"))
    ChatService(engine, completer).parse("hello")
    assert "Corrected:" not in completer.messages[0]["content"]


@pytest.mark.parametrize(
    "text", ["do ghanto lagenge", "kaam ek ghantay ka", "एक घंटा लगेगा", "२० मिनट"]
)
def test_guard_keeps_estimates_for_more_time_words(engine: Engine, text: str) -> None:
    result = ParseResult(intent="create_task", task=ParsedTask(title="t", estimate_min=60))
    response = ChatService(engine, FakeCompleter(result)).parse(text)
    assert response.cards[0].estimate_min == 60


@pytest.mark.parametrize("intent", ["question", "unknown", "create_task"])
def test_llm_written_durations_never_reach_the_reply(engine: Engine, intent: str) -> None:
    result = ParseResult.model_validate(
        {
            "intent": intent,
            "task": {"title": "t"} if intent == "create_task" else None,
            "clarifying_question": "That usually takes about 45 minutes.",
        }
    )
    response = ChatService(engine, FakeCompleter(result)).parse("something")
    assert "45" not in response.reply and response.reply


def test_extra_tasks_alone_still_become_cards(engine: Engine) -> None:
    result = ParseResult(intent="create_task", extra_tasks=[ParsedTask(title="only extra")])
    response = ChatService(engine, FakeCompleter(result)).parse("x 5 min")
    assert response.intent == "create_task"
    assert [c.title for c in response.cards] == ["only extra"]


@pytest.mark.parametrize(
    "bad",
    [
        {"title": "t", "estimate_min": 10**26},
        {"title": "t", "parts": [{"type": "other", "quantity": float("inf")}]},
        {"title": "t", "parts": [{"type": "other", "quantity": 1e12}]},
    ],
)
def test_absurd_llm_numbers_are_rejected_by_the_schema(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):  # pydantic ValidationError
        ParseResult.model_validate({"intent": "create_task", "task": bad})


def test_huge_stored_correction_does_not_bloat_the_prompt(engine: Engine) -> None:
    card = {"title": "x" * 100_000, "parts": [{"part_type_id": "p", "planned_qty": 1}] * 500}
    with session_scope(engine) as s:
        s.add(
            Correction(
                raw_text="y" * 100_000,
                llm_output_json={},
                corrected_json=card,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
    completer = FakeCompleter(ParseResult(intent="unknown"))
    ChatService(engine, completer).parse("hello")
    assert len(completer.messages[0]["content"]) < 15_000


def _example_shown(engine: Engine, raw_text: str, **card: Any) -> str:
    with session_scope(engine) as s:
        s.add(
            Correction(
                raw_text=raw_text,
                llm_output_json={},
                corrected_json={"title": "t", **card},
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
    completer = FakeCompleter(ParseResult(intent="unknown"))
    ChatService(engine, completer).parse("hello")
    return completer.messages[0]["content"].split("## The user's own fixes")[1]


def test_few_shot_hides_an_estimate_the_text_never_said(engine: Engine) -> None:
    shown = _example_shown(engine, "solve the graph sheet", estimate_min=45)
    assert '"estimate_min": null' in shown and "45" not in shown


def test_few_shot_keeps_an_estimate_the_text_said(engine: Engine) -> None:
    shown = _example_shown(engine, "graph sheet, 1 hour", estimate_min=60)
    assert '"estimate_min": 60' in shown


def test_few_shot_hides_a_video_length_used_as_estimate(engine: Engine) -> None:
    _, parts = ids(engine)
    video = [{"part_type_id": parts["video_watch"], "planned_qty": 25}]
    shown = _example_shown(engine, "watch a 25 min video", estimate_min=25, parts=video)
    assert '"estimate_min": null' in shown

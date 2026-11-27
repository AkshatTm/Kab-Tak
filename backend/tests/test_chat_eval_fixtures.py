"""Non-live checks: the eval fixture is well formed and the scorer counts correctly."""

from typing import Any

from app.chat.durations import stated_estimate
from tests.test_chat_eval import FIELDS, GoldLine, load_gold, provider_table, score

CATEGORIES = {"DSA", "Theory subject", "Assignment", "Project coding", "Admin"}
PART_TYPES = {
    "video_watch",
    "read_theory",
    "handwrite_code",
    "implement_code",
    "practice_problem",
    "notes",
    "assignment",
    "project_coding",
    "other",
}


def test_fixture_is_valid_and_covers_required_cases() -> None:
    gold = load_gold()  # pydantic validation of every line
    tasks = [t for line in gold for t in line.tasks]

    assert len(gold) >= 25
    assert len({line.text for line in gold}) == len(gold)
    assert sum(any(t.estimate_min is None for t in line.tasks) for line in gold) >= 6
    assert sum(line.lang == "hinglish" for line in gold) >= 3
    assert {t.category for t in tasks} - {None} == CATEGORIES
    assert {p.type for t in tasks for p in t.parts} <= PART_TYPES
    for line in gold:
        assert bool(line.tasks) == (line.intent == "create_task"), line.text


def _gold() -> GoldLine:
    task: dict[str, Any] = {
        "category": "DSA",
        "estimate_min": 90,
        "tentative": False,
        "familiarity": None,
        "parts": [
            {"type": "video_watch", "quantity": 30},
            {"type": "practice_problem", "quantity": 2},
        ],
    }
    return GoldLine.model_validate(
        {"text": "t", "intent": "create_task", "tasks": [task, {**task, "tentative": True}]}
    )


def test_score_perfect_match_ignores_part_order_and_extra_keys() -> None:
    gold = _gold()
    first, second = (t.model_dump() for t in gold.tasks)
    first["title"] = "anything"
    first["parts"] = [{**p, "unit": "x"} for p in reversed(first["parts"])]
    predicted = {"intent": "create_task", "task": first, "extra_tasks": [second]}

    report = score([(gold, predicted)])

    assert report.correct == report.total
    assert report.total == {"intent": 1, "n_tasks": 1, **{f: 2 for f in FIELDS[2:]}}
    assert report.overall == 1.0
    assert report.mismatches == []


def test_score_counts_wrong_field_and_missing_task() -> None:
    gold = _gold()
    first = {**gold.tasks[0].model_dump(), "estimate_min": 60, "parts": []}
    predicted = {"intent": "create_task", "task": first, "extra_tasks": []}

    report = score([(gold, predicted)])

    assert report.correct == {
        "intent": 1,
        "n_tasks": 0,
        "category": 1,
        "estimate_min": 0,
        "tentative": 1,
        "familiarity": 1,
        "parts": 0,
    }
    assert report.overall == 4 / 12
    assert len(report.mismatches) == 8  # n_tasks + 2 wrong fields + 5 missing-task fields


def test_score_failed_parse_counts_everything_wrong() -> None:
    chatter = GoldLine.model_validate({"text": "hi", "intent": "unknown", "tasks": []})

    report = score([(_gold(), None), (chatter, None)])

    assert sum(report.correct.values()) == 0
    assert sum(report.total.values()) == 14
    assert report.overall == 0.0


def test_gate_fails_when_one_field_is_bad_even_if_overall_passes() -> None:
    cases: list[tuple[GoldLine, dict[str, Any] | None]] = []
    for g in load_gold():
        d = g.model_dump(mode="json")
        tasks = [{**t, "familiarity": None} for t in d["tasks"]]
        predicted = {
            "intent": d["intent"],
            "task": tasks[0] if tasks else None,
            "extra_tasks": tasks[1:],
        }
        cases.append((g, predicted))
    report = score(cases)
    assert report.overall >= 0.90 and not report.passes()


SPEC_SENTENCE = (
    "Video 2, 30 min left on backtracking. Then handwrite both problem codes, then implement "
    "them on laptop. I think 1.5 hours."
)


def test_fixture_covers_the_review_cases() -> None:
    gold = load_gold()
    tasks = [t for line in gold for t in line.tasks]
    assert SPEC_SENTENCE in {line.text for line in gold}
    both = [t for t in tasks if t.estimate_min and any(p.type == "video_watch" for p in t.parts)]
    assert len(both) >= 7  # video length and the user's own estimate in one sentence
    assert sum(t.familiarity is None for t in tasks) < 0.9 * len(tasks)  # null must not pass
    assert {t.familiarity for t in tasks} == {None, "new", "familiar"}


def test_every_gold_estimate_survives_the_code_guard() -> None:
    """A gold label the guard would null could never score: the label or the guard is wrong."""
    for line in load_gold():
        videos = [p.quantity for t in line.tasks for p in t.parts if p.type == "video_watch"]
        for task in line.tasks:
            kept = stated_estimate(task.estimate_min, line.text, videos)
            assert kept == task.estimate_min, line.text


def test_provider_table_shows_every_provider() -> None:
    calls = [("groq", True), ("groq", False), ("groq", True), ("cerebras", False)]
    table = provider_table(calls, ["groq", "cerebras", "gemini"])
    assert [line.split() for line in table.splitlines()[1:]] == [
        ["groq", "2", "1"],
        ["cerebras", "0", "1"],
        ["gemini", "0", "0"],
    ]

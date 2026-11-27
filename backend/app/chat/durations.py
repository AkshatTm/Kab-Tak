"""Durations the user actually wrote (ADR 0004). English, Hinglish and Devanagari.

shortcut: a fixed word list, not a language parser. A missed phrase only nulls the estimate (one tap
on the card); extend the tables when the eval shows one.
"""

import re
from collections.abc import Collection
from dataclasses import dataclass

_WORDS: dict[str, float] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90, "a": 1, "an": 1,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6,
    "saat": 7, "aath": 8, "nau": 9, "das": 10, "gyarah": 11, "barah": 12, "pandrah": 15,
    "bees": 20, "pachees": 25, "pachis": 25, "tees": 30, "chalis": 40, "chaalis": 40,
    "paintalis": 45, "pachas": 50, "dedh": 1.5, "derh": 1.5, "dhai": 2.5, "dhaai": 2.5,
    "adhai": 2.5, "aadha": 0.5, "aadhe": 0.5, "adha": 0.5, "pauna": 0.75,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "दस": 10, "पंद्रह": 15,
    "बीस": 20, "तीस": 30, "डेढ़": 1.5, "ढाई": 2.5, "आधा": 0.5, "आधे": 0.5,
}  # fmt: skip
_MODIFIERS = {
    "sava": 0.25, "sawa": 0.25, "सवा": 0.25, "paune": -0.25, "पौने": -0.25,
    "sadhe": 0.5, "saade": 0.5, "sade": 0.5, "साढ़े": 0.5,
}  # fmt: skip


def _any(words: Collection[str]) -> str:
    return "|".join(sorted(words, key=len, reverse=True))  # longest first: "an" before "a"


_NUMBER = (
    r"three\s+quarters\s+of\s+an?|(?:a\s+)?quarter(?:\s+of)?(?:\s+an?)?|half(?:\s+an?)?"
    r"|(?:a\s+)?couple(?:\s+of)?"
    r"|(?:twenty|thirty|forty|fifty)[\s-](?:one|two|three|four|five|six|seven|eight|nine)"
    rf"|\d+(?:\.\d+)?|(?:{_any(_WORDS)})(?![a-z])"
)
_HOURS = r"hours?|hrs?|ghant(?:on|ay|aa|a|e|o)|(?:घंट|घण्ट|घन्ट)(?:ों|ा|े)?|(?P<h>h)"
_MINUTES = r"minutes?|mins?|minat|minit|मिनट(?:ों)?|(?P<m>m)"
_DURATION = re.compile(
    # not inside a word or a decimal; "1h30m" is the one place a letter may come first
    r"(?:(?<![\w.ऀ-ॿ])|(?<=\dh))"
    rf"(?:(?:(?P<mod>{_any(_MODIFIERS)})\s+)?(?P<num>{_NUMBER})|(?P<alone>{_any(_MODIFIERS)}))"
    r"(?P<half>\s+and\s+a\s+half)?\s*-?\s*"
    rf"(?:(?P<hours>{_HOURS})|{_MINUTES})(?![a-z])"
    r"(?P<tail>\s+and\s+a\s+half)?",
    re.IGNORECASE,
)
_JOIN = re.compile(r"\s*(?:and|aur|&)?\s*", re.IGNORECASE)  # "1 hour and 30 minutes"
_MATERIAL = r"(?:video|lecture|lec|recording)s?"
# "25 min DSA video", "20 minute ka video", "30 min left"; not "30 min for the video"
_MATERIAL_AFTER = re.compile(
    r"\s*(?:(?:long|left|remaining|bacha|bachi|bache)\b|-?\s*(?:(?:of|ka|ki|ke)\s+)?"
    r"(?:(?!(?:for|on|to|in|at|mein|me|lagega|lagenge)\b)\w+\s+){0,2}?"
    rf"{_MATERIAL}\b)",
    re.IGNORECASE,
)
_MATERIAL_BEFORE = re.compile(
    rf"\b{_MATERIAL}\s+(?:is|of|hai|length|:)\s*(?:(?:about|around)\s+)?$", re.IGNORECASE
)


@dataclass(frozen=True)
class Duration:
    minutes: int
    start: int
    end: int
    material: bool  # the length of a video or similar, not a time guess


def _value(match: re.Match[str]) -> float:
    number = " ".join((match["num"] or "").casefold().split())
    modifier = (match["mod"] or match["alone"] or "").casefold()
    if not number:
        value = 1.0  # "sava ghanta"
    elif number[0].isdigit():
        value = float(number)
    elif number.startswith("three quarters"):
        value = 0.75
    elif "quarter" in number:
        value = 0.25
    elif number.startswith("half"):
        value = 0.5
    elif "couple" in number:
        value = 2.0
    else:
        value = sum(_WORDS[w] for w in re.split(r"[\s-]", number))
    if match["half"] or match["tail"]:
        value += 0.5
    return value + _MODIFIERS.get(modifier, 0.0)


def find_durations(text: str) -> list[Duration]:
    found: list[tuple[float, int, int, bool]] = []  # minutes, start, end, is hours
    for m in _DURATION.finditer(text):
        if (m["h"] or m["m"]) and not (m["num"] or "")[-1:].isdigit():
            continue  # a bare h or m only counts after digits
        hours = m["hours"] is not None
        minutes = _value(m) * (60 if hours else 1)
        if found:
            prev, start, end, prev_hours = found[-1]
            if prev_hours and not hours and minutes < 60 and _JOIN.fullmatch(text, end, m.start()):
                found[-1] = (prev + minutes, start, m.end(), False)
                continue
        found.append((minutes, m.start(), m.end(), hours))
    return [
        Duration(
            round(minutes),
            start,
            end,
            bool(_MATERIAL_AFTER.match(text, end) or _MATERIAL_BEFORE.search(text, 0, start)),
        )
        for minutes, start, end, _ in found
    ]


def stated_estimate(
    estimate: int | None, text: str, video_quantities: Collection[float] = ()
) -> int | None:
    """The estimate if the user wrote that duration as their own guess, otherwise None."""
    same = [d for d in find_durations(text) if d.minutes == estimate]
    if not any(not d.material for d in same):
        return None
    if estimate in video_quantities and len(same) < 2:
        return None  # the only mention is the video's length
    return estimate


# what removing a duration leaves behind: empty brackets, a dangling "for" / "about"
_FILLER = r"(?:~|≈|\b(?:about|approx\.?|around|for|in)\b)"
_EMPTY_BRACKETS = re.compile(rf"[(\[]\s*(?:{_FILLER}\s*)*[)\]]", re.IGNORECASE)
_DANGLING = re.compile(rf"(?:[\s\-–—:,;|]*{_FILLER})+\s*$", re.IGNORECASE)


def strip_unsaid(title: str, text: str) -> str:
    """The title without any duration the user did not write; may come back empty."""
    said = {d.minutes for d in find_durations(text)}
    unsaid = [d for d in find_durations(title) if d.minutes not in said]
    if not unsaid:
        return title
    for d in reversed(unsaid):
        title = title[: d.start] + title[d.end :]
    title = _DANGLING.sub("", _EMPTY_BRACKETS.sub("", title))
    return " ".join(title.split()).strip(" -–—:,;|~≈")

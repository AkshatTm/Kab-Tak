import pytest

from app.chat.durations import find_durations


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("90 min", [90]),
        ("90mins", [90]),
        ("1.5 hours", [90]),
        ("2 hrs", [120]),
        ("graphs 45m", [45]),
        ("2h", [120]),
        ("1 hour 30 minutes", [90]),
        ("1h 30m", [90]),
        ("half an hour", [30]),
        ("a quarter of an hour", [15]),
        ("an hour and a half", [90]),
        ("2 and a half hours", [150]),
        ("a couple of hrs", [120]),
        ("forty five minutes", [45]),
        ("twenty-five min", [25]),
        ("ek ghanta", [60]),
        ("dedh ghanta", [90]),
        ("aadha ghanta", [30]),
        ("dhai ghante", [150]),
        ("sava ghanta", [75]),
        ("sava do ghante", [135]),
        ("paune do ghante", [105]),
        ("sadhe teen ghante", [210]),
        ("2 ghante", [120]),
        ("do ghanto lagenge", [120]),
        ("kaam ek ghantay ka", [60]),
        ("das minute ka kaam", [10]),
        ("एक घंटा लगेगा", [60]),
        ("डेढ़ घंटे", [90]),
        ("२० मिनट", [20]),
        ("20 min video, total 35 min", [20, 35]),
        ("1h30", [90]),
        ("1hr30", [90]),
        ("1 ghanta 30", [90]),
        ("1 hour 30", [90]),
        ("1 hour 30 lagega", [90]),
        ("1 hour, 30 minutes", [90]),
        ("1,5 hours", [90]),
        ("1 hour 20 problems", [60]),
        ("saadhe teen ghante", [210]),
        ("pona ghanta", [45]),
        ("paun ghanta", [45]),
        ("adha ghnta", [30]),
        ("2 ghnte", [120]),
        ("45 मिनिट", [45]),
        ("पैंतालीस मिनट", [45]),
        ("pachpan minute", [55]),
        # not durations
        ("one hundred twenty minutes", []),
        ("Solve 3 problems", []),
        ("admin stuff, twenty", []),
        ("do the second assignment", []),
        ("minimum spanning tree, 2 hashmaps", []),
        ("watch video 2", []),
    ],
)
def test_find_durations(text: str, minutes: list[int]) -> None:
    assert [d.minutes for d in find_durations(text)] == minutes


@pytest.mark.parametrize(
    ("text", "material"),
    [
        ("Watch a 25 minute DSA video on tries", [True]),
        ("Watch 40 minutes of DSA lecture video, I'll need 60 min", [True, False]),
        ("Video 2, 30 min left on backtracking. I think 1.5 hours", [True, False]),
        ("DSA ka 20 minute ka video, total 35 min lagenge", [True, False]),
        ("the video is 25 min long, give me 40 min", [True, False]),
        ("I need 30 min for the video", [False]),
        ("watch the video, 45 min", [False]),
        ("lecture: 40 min", [True]),
        ("lecture (40 min)", [True]),
        ("video 30 min", [True]),
        ("DSA video (30 min)", [True]),
        ("30 min youtube tutorial", [True]),
        ("the video's 30 min", [True]),
        ("30 मिनट का वीडियो", [True]),
    ],
)
def test_material_lengths_are_marked(text: str, material: list[bool]) -> None:
    assert [d.material for d in find_durations(text)] == material

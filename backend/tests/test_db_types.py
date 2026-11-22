from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, insert, select, text
from sqlalchemy.exc import StatementError

from app.db.types import UTCDateTime

t = Table("t", MetaData(), Column("at", UTCDateTime))


def test_roundtrip_converts_offset_to_utc() -> None:
    eng = create_engine("sqlite://")
    t.create(eng)
    ist = timezone(timedelta(hours=5, minutes=30))
    sent = datetime(2026, 1, 1, 9, 0, tzinfo=ist)
    with eng.begin() as c:
        c.execute(insert(t).values(at=sent))
        got = c.execute(select(t.c.at)).scalar_one()
        raw = c.execute(text("SELECT at FROM t")).scalar_one()
    assert got == sent and got.tzinfo is UTC
    assert got.hour == 3 and got.minute == 30
    assert raw.startswith("2026-01-01 03:30")


def test_naive_raises() -> None:
    eng = create_engine("sqlite://")
    t.create(eng)
    with pytest.raises(StatementError, match="naive") as e, eng.begin() as c:
        c.execute(insert(t).values(at=datetime(2026, 1, 1)))
    assert isinstance(e.value.orig, ValueError)


def test_none_passes() -> None:
    eng = create_engine("sqlite://")
    t.create(eng)
    with eng.begin() as c:
        c.execute(insert(t).values(at=None))
        assert c.execute(select(t.c.at)).scalar_one() is None

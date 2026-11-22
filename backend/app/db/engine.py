from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url


def make_engine(url: str) -> Engine:
    u = make_url(url)
    sqlite = u.drivername.startswith("sqlite")
    if sqlite and u.database and u.database != ":memory:":
        Path(u.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if sqlite:

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn: Any, _record: Any) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def check(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True

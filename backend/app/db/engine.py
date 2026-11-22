from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url


def make_engine(url: str) -> Engine:
    u = make_url(url)
    if u.drivername.startswith("sqlite") and u.database and u.database != ":memory:":
        Path(u.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def check(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True

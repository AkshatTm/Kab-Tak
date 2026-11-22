import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

import app.db.models  # noqa: F401  (registers tables)
from app.db.engine import make_engine
from app.db.migrate import MIGRATIONS_DIR, upgrade_with_backup


def _url(p: Path) -> str:
    return f"sqlite:///{p.as_posix()}"


def test_fresh_upgrade_creates_tables_and_seeds(tmp_path: Path) -> None:
    url = _url(tmp_path / "data.db")
    upgrade_with_backup(url)
    eng = make_engine(url)
    names = set(inspect(eng).get_table_names())
    assert set(SQLModel.metadata.tables) <= names and len(SQLModel.metadata.tables) == 10
    with eng.connect() as c:
        assert c.execute(text("SELECT count(*) FROM part_types")).scalar_one() == 9
        assert c.execute(text("SELECT count(*) FROM categories")).scalar_one() == 5
        day = c.execute(text("SELECT value_json FROM settings WHERE key='day_starts_at'"))
        inst = c.execute(text("SELECT value_json FROM settings WHERE key='installed_at'"))
        assert json.loads(day.scalar_one()) == "04:00"
        assert datetime.fromisoformat(json.loads(inst.scalar_one())).tzinfo is not None
    assert list(tmp_path.glob("*.bak-*")) == []


def test_second_upgrade_is_noop_without_backup(tmp_path: Path) -> None:
    url = _url(tmp_path / "data.db")
    upgrade_with_backup(url)
    upgrade_with_backup(url)
    assert list(tmp_path.glob("*.bak-*")) == []


def _script_dir(root: Path, revs: int) -> Path:
    d = root / "scripts"
    (d / "versions").mkdir(parents=True)
    shutil.copy(MIGRATIONS_DIR / "env.py", d / "env.py")
    shutil.copy(MIGRATIONS_DIR / "script.py.mako", d / "script.py.mako")
    for n in range(1, revs + 1):
        down = "None" if n == 1 else f"'r{n - 1}'"
        sql = "CREATE TABLE a (x INT)" if n == 1 else "CREATE TABLE b (y INT)"
        (d / "versions" / f"r{n}.py").write_text(
            f"from alembic import op\nrevision = 'r{n}'\ndown_revision = {down}\n"
            f"def upgrade() -> None:\n    op.execute('{sql}')\n"
        )
    return d


def test_backup_before_upgrade(tmp_path: Path) -> None:
    db = tmp_path / "data.db"
    url = _url(db)
    upgrade_with_backup(url, str(_script_dir(tmp_path, 1)))
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO a VALUES (7)")
    shutil.rmtree(tmp_path / "scripts")
    upgrade_with_backup(url, str(_script_dir(tmp_path, 2)))
    bak = tmp_path / "data.db.bak-r1"
    assert bak.exists()
    with sqlite3.connect(bak) as c:
        assert c.execute("SELECT x FROM a").fetchall() == [(7,)]
        assert c.execute("SELECT name FROM sqlite_master WHERE name='b'").fetchall() == []
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchall() == [("r2",)]


def test_pragmas(tmp_path: Path) -> None:
    eng = make_engine(_url(tmp_path / "p.db"))
    with eng.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert c.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"


def test_migration_matches_models(migrated_url: str) -> None:
    """No drift: autogenerate against the migrated DB finds nothing to change."""
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from sqlmodel import SQLModel

    from app.db.engine import make_engine

    engine = make_engine(migrated_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    engine.dispose()
    assert diff == []

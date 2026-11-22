import sqlite3
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from app.db.engine import make_engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def upgrade_with_backup(url: str, script_location: str | Path = MIGRATIONS_DIR) -> None:
    """Back up an existing, already-migrated DB before upgrading to head (D2). Raises on failure."""
    cfg = Config()
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    db = make_url(url).database
    if db and db != ":memory:" and Path(db).exists():
        engine = make_engine(url)
        try:
            with engine.connect() as conn:
                current = MigrationContext.configure(conn).get_current_revision()
        finally:
            engine.dispose()
        bak = Path(f"{db}.bak-{current}")
        # never overwrite: a retry after a half-failed migration would replace the clean copy
        if current is not None and current != head and not bak.exists():
            with (
                closing(sqlite3.connect(db)) as src,
                closing(sqlite3.connect(bak)) as dst,
            ):
                src.backup(dst)  # includes un-checkpointed WAL pages
    command.upgrade(cfg, "head")

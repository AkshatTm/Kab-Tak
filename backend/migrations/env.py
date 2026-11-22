from alembic import context
from sqlmodel import SQLModel

import app.db.models  # noqa: F401  (registers tables on the metadata)
from app.db.engine import make_engine

config = context.config
engine = make_engine(config.get_main_option("sqlalchemy.url") or "")
with engine.connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=SQLModel.metadata,
        render_as_batch=True,  # SQLite ALTER support
    )
    # SQLite batch ALTER drops and recreates tables; FK enforcement must be off meanwhile
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

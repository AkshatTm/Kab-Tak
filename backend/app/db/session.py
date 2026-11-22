from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise

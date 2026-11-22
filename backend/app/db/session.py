from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:  # callers read rows after commit
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__
from app.db.engine import check

router = APIRouter()


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    db: Literal["ok", "error"]


@router.get("/api/health")
def health(request: Request) -> Health:
    ok = check(request.app.state.get_engine())
    return Health(status="ok", version=__version__, db="ok" if ok else "error")

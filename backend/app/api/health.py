from importlib.metadata import version
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db.engine import check

router = APIRouter()


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    db: Literal["ok", "error"]


@router.get("/api/health")
def health(request: Request) -> Health:
    # shortcut: package metadata is missing in a PyInstaller bundle, switch to a constant in S4
    ok = check(request.app.state.get_engine())
    return Health(status="ok", version=version("backend"), db="ok" if ok else "error")

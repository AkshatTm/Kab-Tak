import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.middleware.base import RequestResponseEndpoint

from app.api.health import router as health_router
from app.api.tasks import register_errors
from app.api.tasks import router as tasks_router
from app.db.engine import make_engine
from app.db.migrate import upgrade_with_backup
from app.settings import Settings
from app.timer.clock import Clock, SystemClock
from app.timer.service import TaskService

ORIGINS = ["http://localhost:5173", "http://tauri.localhost"]


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        upgrade_with_backup(settings.resolved_db_url())  # failure raises: app must not start
        yield

    app = FastAPI(title="Kab Tak", lifespan=lifespan)

    @cache  # lazy: building the app (e.g. for openapi) never touches the DB file
    def get_engine() -> Engine:
        return make_engine(settings.resolved_db_url())

    app.state.get_engine = get_engine

    the_clock = clock or SystemClock()

    @cache
    def get_service() -> TaskService:
        return TaskService(get_engine(), the_clock)

    app.state.get_service = get_service

    @app.middleware("http")
    async def require_token(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api/"):
            given = request.headers.get("X-KabTak-Token", "")
            if not settings.token or not secrets.compare_digest(
                given.encode(), settings.token.encode()
            ):
                return JSONResponse({"detail": "invalid token"}, status_code=401)
        return await call_next(request)

    # added last = outermost, so CORS answers preflight before the token check
    app.add_middleware(
        CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(health_router)
    app.include_router(tasks_router)
    register_errors(app)
    return app


app = create_app()

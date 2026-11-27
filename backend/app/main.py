import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.middleware.base import RequestResponseEndpoint

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.tasks import register_errors
from app.api.tasks import router as tasks_router
from app.chat.service import ChatService, Completer
from app.db.engine import make_engine
from app.db.migrate import upgrade_with_backup
from app.llm.chain import LlmChain
from app.llm.config import ProviderKeys, load_config
from app.settings import Settings
from app.timer.clock import Clock, SystemClock
from app.timer.service import TaskService

ORIGINS = ["http://localhost:5173", "http://tauri.localhost"]


def create_app(
    settings: Settings | None = None,
    clock: Clock | None = None,
    completer: Completer | None = None,
) -> FastAPI:
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

    @cache  # no LLM client is built until the first chat request
    def get_chat() -> ChatService:
        llm = completer or LlmChain(load_config(), ProviderKeys(), get_engine())
        return ChatService(get_engine(), llm)

    app.state.get_chat = get_chat

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
    app.include_router(chat_router)
    register_errors(app)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        # without "input": echoing text that is not valid UTF-8 would turn the 422 into a 500
        detail = [{k: e[k] for k in ("type", "loc", "msg")} for e in exc.errors()]
        return JSONResponse({"detail": detail}, status_code=422)

    return app


app = create_app()

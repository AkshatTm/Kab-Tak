from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.schemas import CategoryOut, ConflictOut, ErrorOut, PartTypeOut, TaskOut
from app.timer.inputs import PauseIn, StopIn, TaskCreate, TaskPatch
from app.timer.machine import InvalidAt, InvalidTransition
from app.timer.service import AlreadyRunning, BadInput, NotFound, TaskService

router = APIRouter(prefix="/api")


def get_service(request: Request) -> TaskService:
    svc: TaskService = request.app.state.get_service()
    return svc


Svc = Annotated[TaskService, Depends(get_service)]
ERR: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorOut},
    409: {"model": ConflictOut},
    422: {"model": ErrorOut},
}


@router.post("/tasks", status_code=201)
def create_task(body: TaskCreate, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.create_task(body))


@router.get("/tasks")
def list_tasks(svc: Svc, date: date | None = None) -> list[TaskOut]:
    return [TaskOut.of(v) for v in svc.list_tasks(date)]


# declared before /tasks/{task_id} so "running" is not read as an id
@router.get("/tasks/running")
def running_task(svc: Svc) -> TaskOut | None:
    v = svc.running_task()
    return TaskOut.of(v) if v else None


@router.get("/tasks/{task_id}", responses=ERR)
def get_task(task_id: str, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.get_task(task_id))


@router.patch("/tasks/{task_id}", responses=ERR)
def patch_task(task_id: str, body: TaskPatch, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.update_task(task_id, body))


@router.post("/tasks/{task_id}/start", responses=ERR)
def start(task_id: str, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.start(task_id))


@router.post("/tasks/{task_id}/pause", responses=ERR)
def pause(task_id: str, svc: Svc, body: PauseIn | None = None) -> TaskOut:
    return TaskOut.of(svc.pause(task_id, body or PauseIn()))


@router.post("/tasks/{task_id}/resume", responses=ERR)
def resume(task_id: str, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.resume(task_id))


@router.post("/tasks/{task_id}/stop", responses=ERR)
def stop(task_id: str, body: StopIn, svc: Svc) -> TaskOut:
    return TaskOut.of(svc.stop(task_id, body))


@router.get("/categories")
def categories(svc: Svc) -> list[CategoryOut]:
    return [CategoryOut(**c.model_dump()) for c in svc.categories()]


@router.get("/part-types")
def part_types(svc: Svc) -> list[PartTypeOut]:
    return [PartTypeOut(**p.model_dump()) for p in svc.part_types()]


def register_errors(app: FastAPI) -> None:
    def handler(status: int) -> Callable[[Request, Exception], JSONResponse]:
        def fn(_: Request, exc: Exception) -> JSONResponse:
            body: dict[str, str | None] = {"detail": str(exc)}
            if isinstance(exc, AlreadyRunning):
                body["running_task_id"] = exc.task_id
            return JSONResponse(body, status_code=status)

        return fn

    app.add_exception_handler(NotFound, handler(404))
    app.add_exception_handler(AlreadyRunning, handler(409))
    app.add_exception_handler(InvalidTransition, handler(409))
    app.add_exception_handler(InvalidAt, handler(422))
    app.add_exception_handler(BadInput, handler(422))

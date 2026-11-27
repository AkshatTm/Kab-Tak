from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import AfterValidator, BaseModel, StringConstraints

from app.chat.service import ChatResponse, ChatService
from app.timer.inputs import TaskCreate, no_surrogates

router = APIRouter(prefix="/api")


Text = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
    AfterValidator(no_surrogates),
]


class ChatIn(BaseModel):
    text: Text


class CorrectionIn(BaseModel):
    raw_text: Text
    llm_output_json: dict[str, Any] | None = None  # null when the parse failed
    corrected_json: TaskCreate


class CorrectionOut(BaseModel):
    id: str


def get_chat(request: Request) -> ChatService:
    svc: ChatService = request.app.state.get_chat()
    return svc


Chat = Annotated[ChatService, Depends(get_chat)]


@router.post("/chat")
def chat(body: ChatIn, svc: Chat) -> ChatResponse:
    return svc.parse(body.text)


@router.post("/corrections", status_code=201)
def add_correction(body: CorrectionIn, svc: Chat) -> CorrectionOut:
    return CorrectionOut(
        id=svc.add_correction(body.raw_text, body.llm_output_json, body.corrected_json)
    )

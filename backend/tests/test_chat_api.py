from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.engine import make_engine
from app.db.models import LlmCall
from app.llm.chain import LlmChain
from app.llm.config import ProviderKeys, load_config
from app.main import create_app
from app.settings import Settings
from tests.fakeclock import FakeClock

H = {"X-KabTak-Token": "t0k"}
SENTENCE = "Backtracking video 2 finish + 2 problems, I think 90 min"
PARSED = {
    "intent": "create_task",
    "task": {
        "title": "Backtracking video 2 + 2 problems",
        "category": "DSA",
        "estimate_min": 90,
        "parts": [{"type": "practice_problem", "quantity": 2, "unit": "problems"}],
    },
}


class FakeCompleter:
    def __init__(self, result: dict[str, Any] | None) -> None:
        self.result = result
        self.messages: list[list[dict[str, str]]] = []

    def complete_json(self, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        self.messages.append(messages)
        return None if self.result is None else schema.model_validate(self.result)


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'chat.db').as_posix()}"


@pytest.fixture
def fake() -> FakeCompleter:
    return FakeCompleter(PARSED)


@pytest.fixture
def client(db_url: str, fake: FakeCompleter) -> Iterator[TestClient]:
    app = create_app(Settings(token="t0k", db_url=db_url), FakeClock(), fake)
    with TestClient(app, headers=H) as c:
        yield c


def test_routes_need_the_token(client: TestClient) -> None:
    bare = TestClient(client.app)
    assert bare.post("/api/chat", json={"text": "x"}).status_code == 401
    assert bare.post("/api/corrections", json={}).status_code == 401


def test_chat_card_confirms_unchanged(client: TestClient) -> None:
    body = client.post("/api/chat", json={"text": SENTENCE}).json()
    assert body["parsed"] is True and body["intent"] == "create_task"
    created = client.post("/api/tasks", json=body["cards"][0])
    assert created.status_code == 201, created.text
    task = client.get(f"/api/tasks/{created.json()['id']}").json()
    assert (task["status"], task["source"], task["raw_text"]) == ("ready", "chat", SENTENCE)
    assert task["estimate_min"] == 90 and task["parts"][0]["planned_qty"] == 2


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_text_is_422(client: TestClient, text: str) -> None:
    assert client.post("/api/chat", json={"text": text}).status_code == 422


def test_all_providers_failing_is_200_with_manual_card(db_url: str) -> None:
    app = create_app(Settings(token="t0k", db_url=db_url), FakeClock(), FakeCompleter(None))
    with TestClient(app, headers=H) as c:
        r = c.post("/api/chat", json={"text": "do the thing"})
    assert r.status_code == 200 and r.json()["parsed"] is False
    assert r.json()["cards"][0]["title"] == "do the thing"


def test_correction_is_stored_and_fed_back_with_names(
    client: TestClient, fake: FakeCompleter
) -> None:
    body = client.post("/api/chat", json={"text": SENTENCE}).json()
    card = {**body["cards"][0], "title": "My fixed title"}
    r = client.post(
        "/api/corrections",
        json={"raw_text": SENTENCE, "llm_output_json": body["parse_json"], "corrected_json": card},
    )
    assert r.status_code == 201 and r.json()["id"]
    client.post("/api/chat", json={"text": "next one, 20 min"})
    prompt = fake.messages[-1][0]["content"]
    assert "My fixed title" in prompt
    assert '"category": "DSA"' in prompt and '"type": "practice_problem"' in prompt
    assert card["category_id"] not in prompt  # ids teach the model nothing


def test_bad_correction_is_422(client: TestClient) -> None:
    r = client.post(
        "/api/corrections",
        json={"raw_text": "x", "llm_output_json": {}, "corrected_json": {"title": ""}},
    )
    assert r.status_code == 422


def test_api_key_never_reaches_response_or_db(db_url: str) -> None:
    secret = "sk-very-secret-key"

    def echo_key(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"bad key {secret}"}})

    engine = make_engine(db_url)
    keys = ProviderKeys(_env_file=None, groq_api_key=secret, cerebras_api_key="", gemini_api_key="")
    chain = LlmChain(
        load_config(), keys, engine, httpx.Client(transport=httpx.MockTransport(echo_key))
    )
    app = create_app(Settings(token="t0k", db_url=db_url), FakeClock(), chain)
    with TestClient(app, headers=H) as c:
        r = c.post("/api/chat", json={"text": "anything 10 min"})
    assert r.status_code == 200 and secret not in r.text
    with Session(engine) as s:
        rows = s.exec(select(LlmCall)).all()
        assert rows and all(secret not in (row.error or "") for row in rows)
    engine.dispose()

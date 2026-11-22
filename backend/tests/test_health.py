from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

TOKEN = {"X-KabTak-Token": "t0k"}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    s = Settings(token="t0k", db_url=f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(create_app(s)) as c:
        yield c


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/health", headers=TOKEN)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert isinstance(body["version"], str)


def test_health_no_token(client: TestClient) -> None:
    assert client.get("/api/health").status_code == 401


def test_health_wrong_token(client: TestClient) -> None:
    assert client.get("/api/health", headers={"X-KabTak-Token": "nope"}).status_code == 401


def _preflight(client: TestClient, origin: str) -> str | None:
    r = client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-kabtak-token",
        },
    )
    origin_header: str | None = r.headers.get("access-control-allow-origin")
    return origin_header


def test_cors_allowed_origin(client: TestClient) -> None:
    assert _preflight(client, "http://localhost:5173") == "http://localhost:5173"


def test_cors_disallowed_origin(client: TestClient) -> None:
    assert _preflight(client, "http://evil.example") is None

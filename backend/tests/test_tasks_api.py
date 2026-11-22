from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from tests.fakeclock import FakeClock

H = {"X-KabTak-Token": "t0k"}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'api.db').as_posix()}"


@pytest.fixture
def client(db_url: str, clock: FakeClock) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(token="t0k", db_url=db_url), clock), headers=H) as c:
        yield c


def new(client: TestClient, title: str = "t", **kw: Any) -> dict[str, Any]:
    body = {"title": title, "estimate_min": 60, **kw}
    r = client.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    out: dict[str, Any] = r.json()
    return out


def test_lifecycle_over_http(client: TestClient, clock: FakeClock) -> None:
    t = new(client)
    assert t["status"] == "ready" and t["created_at"].endswith("Z")
    tid = t["id"]
    assert client.post(f"/api/tasks/{tid}/start").json()["status"] == "running"
    clock.advance(10)
    assert client.post(f"/api/tasks/{tid}/pause", json={}).json()["status"] == "paused"
    clock.advance(5)
    assert client.post(f"/api/tasks/{tid}/resume").json()["status"] == "running"
    clock.advance(10)
    done = client.post(f"/api/tasks/{tid}/stop", json={"outcome": "done"}).json()
    assert (done["status"], done["active_min"], done["wall_min"]) == ("stopped", 20, 25)
    assert client.get(f"/api/tasks/{tid}").json()["outcome"] == "done"


def test_every_task_route_needs_the_token(client: TestClient) -> None:
    bare = TestClient(client.app)
    for method, path in [
        ("get", "/api/tasks"),
        ("get", "/api/tasks/running"),
        ("get", "/api/tasks/x"),
        ("post", "/api/tasks"),
        ("post", "/api/tasks/x/start"),
        ("get", "/api/categories"),
        ("get", "/api/part-types"),
    ]:
        assert getattr(bare, method)(path).status_code == 401, path


def test_second_start_is_409_with_running_id(client: TestClient) -> None:
    a, b = new(client, "a")["id"], new(client, "b")["id"]
    assert client.post(f"/api/tasks/{a}/start").status_code == 200
    r = client.post(f"/api/tasks/{b}/start")
    assert r.status_code == 409 and r.json()["running_task_id"] == a


def test_bad_at_is_422(client: TestClient, clock: FakeClock) -> None:
    tid = new(client)["id"]
    start = clock.now()
    client.post(f"/api/tasks/{tid}/start")
    clock.advance(10)
    early = (start - timedelta(minutes=1)).isoformat()
    future = (clock.now() + timedelta(minutes=1)).isoformat()
    for at in (early, future, "2026-01-01T12:05:00"):  # last one has no timezone
        assert client.post(f"/api/tasks/{tid}/pause", json={"at": at}).status_code == 422
    assert (
        client.post(f"/api/tasks/{tid}/stop", json={"outcome": "done", "at": early}).status_code
        == 422
    )
    assert client.get(f"/api/tasks/{tid}").json()["status"] == "running"


def test_running_endpoint_and_restart(db_url: str, clock: FakeClock) -> None:
    settings = Settings(token="t0k", db_url=db_url)
    with TestClient(create_app(settings, clock), headers=H) as c:
        assert c.get("/api/tasks/running").json() is None
        tid = new(c)["id"]
        c.post(f"/api/tasks/{tid}/start")
        running = c.get("/api/tasks/running").json()
        assert running["id"] == tid and running["open_session_start"].endswith("Z")
    with TestClient(create_app(settings, clock), headers=H) as c2:  # "restart"
        again = c2.get("/api/tasks/running").json()
        assert again["id"] == tid and again["open_session_start"] == running["open_session_start"]


def test_list_by_study_day(client: TestClient, clock: FakeClock) -> None:
    clock.advance(7 * 60)  # 00:30 local on Jan 2 -> study day Jan 1
    late = new(client, "late")["id"]
    client.post(f"/api/tasks/{late}/start")
    clock.advance(3.5 * 60)  # 04:00 local -> study day Jan 2
    new(client, "fresh")

    def titles(d: str) -> list[str]:
        return [t["title"] for t in client.get("/api/tasks", params={"date": d}).json()]

    assert titles("2026-01-01") == ["late"]
    assert titles("2026-01-02") == ["fresh"]
    assert [t["title"] for t in client.get("/api/tasks").json()] == ["fresh"]


def test_lookups(client: TestClient) -> None:
    cats = client.get("/api/categories").json()
    assert {c["name"] for c in cats} == {
        "DSA",
        "Theory subject",
        "Assignment",
        "Project coding",
        "Admin",
    }
    assert len(client.get("/api/part-types").json()) == 9


def test_draft_then_estimate(client: TestClient) -> None:
    r = client.post("/api/tasks", json={"title": "no guess"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    tid = r.json()["id"]
    assert client.post(f"/api/tasks/{tid}/start").status_code == 409
    patched = client.patch(f"/api/tasks/{tid}", json={"estimate_min": 25}).json()
    assert patched["status"] == "ready" and patched["estimate_min"] == 25
    assert client.post(f"/api/tasks/{tid}/start").status_code == 200


def test_parts_roundtrip_and_validation(client: TestClient) -> None:
    pt = client.get("/api/part-types").json()[0]["id"]
    t = new(client, parts=[{"part_type_id": pt, "planned_qty": 4}])
    assert t["parts"][0]["planned_qty"] == 4
    tid = t["id"]
    client.post(f"/api/tasks/{tid}/start")
    bad = client.post(
        f"/api/tasks/{tid}/stop",
        json={"outcome": "partly", "completed_parts": [{"part_id": "nope", "completed_qty": 1}]},
    )
    assert bad.status_code == 422
    ok = client.post(
        f"/api/tasks/{tid}/stop",
        json={
            "outcome": "partly",
            "completed_parts": [{"part_id": t["parts"][0]["id"], "completed_qty": 2}],
        },
    )
    assert ok.json()["parts"][0]["completed_qty"] == 2
    assert client.post("/api/tasks", json={"title": "x", "estimate_min": 0}).status_code == 422


def test_unknown_id_is_404_and_bad_transition_409(client: TestClient) -> None:
    assert client.get("/api/tasks/nope").status_code == 404
    assert client.post("/api/tasks/nope/start").status_code == 404
    tid = new(client)["id"]
    assert client.post(f"/api/tasks/{tid}/pause", json={}).status_code == 409

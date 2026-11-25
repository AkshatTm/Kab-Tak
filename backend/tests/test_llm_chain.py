import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from app.db.engine import make_engine
from app.db.models import LlmCall
from app.llm.chain import LlmChain
from app.llm.config import LlmConfig, ProviderConfig, ProviderKeys, load_config

KEYS = {"a": "sk-secret-aaa", "b": "sk-secret-bbb", "c": "sk-secret-ccc"}
CONFIG = LlmConfig(
    timeout_s=8,
    providers=(
        ProviderConfig("a", "https://a.test/v1", "model-a", "GROQ_API_KEY"),
        ProviderConfig("b", "https://b.test/v1", "model-b", "CEREBRAS_API_KEY"),
        ProviderConfig("c", "https://c.test/v1", "model-c", "GEMINI_API_KEY"),
    ),
)
MESSAGES = [{"role": "user", "content": "hello"}]
GOOD = '{"answer": 42}'

Step = httpx.Response | type[httpx.TransportError]


class Answer(BaseModel):
    answer: int


def keys(a: str = KEYS["a"], b: str = KEYS["b"], c: str = KEYS["c"]) -> ProviderKeys:
    # every field explicit + no env file: the developer's real keys are never read
    return ProviderKeys(_env_file=None, groq_api_key=a, cerebras_api_key=b, gemini_api_key=c)


def completion(content: str | None, usage: bool = True) -> httpx.Response:
    body: dict[str, Any] = {
        "id": "x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }
    if usage:
        body["usage"] = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
    return httpx.Response(200, json=body)


class Script:
    """Per-provider queue of replies; records every request."""

    def __init__(self, **steps: list[Step]) -> None:
        self.steps = steps
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self.steps[request.url.host.split(".")[0]].pop(0)
        if isinstance(step, httpx.Response):
            return step
        raise step("boom", request=request)

    def hosts(self) -> list[str]:
        return [r.url.host.split(".")[0] for r in self.requests]

    def body(self, i: int) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(self.requests[i].content)
        return result


@pytest.fixture
def engine(migrated_url: str) -> Iterator[Engine]:
    eng = make_engine(migrated_url)
    yield eng
    eng.dispose()


Run = Callable[..., Answer | None]


@pytest.fixture
def run(engine: Engine) -> Iterator[Run]:
    clients: list[httpx.Client] = []

    def _run(script: Script, provider_keys: ProviderKeys | None = None) -> Answer | None:
        client = httpx.Client(transport=httpx.MockTransport(script))
        clients.append(client)
        chain = LlmChain(CONFIG, provider_keys or keys(), engine, http_client=client)
        return chain.complete_json(MESSAGES, Answer)

    yield _run
    for client in clients:
        client.close()


def rows(engine: Engine) -> list[LlmCall]:
    with Session(engine) as s:
        return list(s.exec(select(LlmCall).order_by(LlmCall.created_at)))  # type: ignore[arg-type]


def test_success_returns_model_and_logs_tokens(run: Run, engine: Engine) -> None:
    script = Script(a=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    [row] = rows(engine)
    assert (row.provider, row.model, row.ok, row.error) == ("a", "model-a", True, None)
    assert (row.prompt_tokens, row.completion_tokens) == (11, 7)
    assert row.latency_ms >= 0


def test_request_shape(run: Run) -> None:
    script = Script(a=[completion(GOOD)])
    run(script)
    [request] = script.requests
    assert str(request.url) == "https://a.test/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {KEYS['a']}"
    assert request.extensions["timeout"]["read"] == 8
    body = script.body(0)
    assert body["model"] == "model-a"
    assert body["messages"] == MESSAGES
    assert body["response_format"] == {"type": "json_object"}


def test_missing_usage_is_fine(run: Run, engine: Engine) -> None:
    assert run(Script(a=[completion(GOOD, usage=False)])) == Answer(answer=42)
    [row] = rows(engine)
    assert (row.prompt_tokens, row.completion_tokens) == (None, None)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_http_error_falls_through_without_retry(run: Run, engine: Engine, status: int) -> None:
    script = Script(a=[httpx.Response(status, json={"error": "nope"})], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "b"]
    first, second = rows(engine)
    assert (first.provider, first.ok) == ("a", False)
    assert first.error is not None and str(status) in first.error
    assert (second.provider, second.ok) == ("b", True)


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_failure_falls_through(
    run: Run, engine: Engine, failure: type[httpx.TransportError]
) -> None:
    script = Script(a=[failure], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "b"]
    assert [r.ok for r in rows(engine)] == [False, True]
    assert rows(engine)[0].error


def test_bad_json_is_repaired_with_the_validation_error(run: Run, engine: Engine) -> None:
    script = Script(a=[completion('{"answer": "many"}'), completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "a"]
    repair = script.body(1)["messages"]
    assert repair[: len(MESSAGES)] == MESSAGES
    assert repair[-2] == {"role": "assistant", "content": '{"answer": "many"}'}
    assert repair[-1]["role"] == "user"
    assert "int_parsing" in repair[-1]["content"]
    assert script.body(1)["response_format"] == {"type": "json_object"}
    first, second = rows(engine)
    assert (first.ok, second.ok) == (False, True)
    assert first.error is not None and "int_parsing" in first.error
    assert first.prompt_tokens == 11


def test_bad_json_twice_moves_on_with_original_messages(run: Run, engine: Engine) -> None:
    script = Script(a=[completion("nope"), completion("still nope")], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "a", "b"]
    assert script.body(2)["messages"] == MESSAGES
    assert [r.ok for r in rows(engine)] == [False, False, True]


def test_http_error_on_repair_call_falls_through(run: Run, engine: Engine) -> None:
    script = Script(a=[completion("nope"), httpx.Response(429)], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "a", "b"]
    assert [r.ok for r in rows(engine)] == [False, False, True]


@pytest.mark.parametrize(
    "bad",
    [
        completion(None),
        completion(""),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"choices": [{"index": 0}]}),
        httpx.Response(200, text="<html>gateway</html>"),
    ],
    ids=["null-content", "empty-content", "no-choices", "empty-body", "no-message", "html"],
)
def test_reply_without_content_is_invalid(run: Run, engine: Engine, bad: httpx.Response) -> None:
    script = Script(a=[bad, bad], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "a", "b"]
    assert [r.ok for r in rows(engine)] == [False, False, True]


def test_unparseable_json_body_falls_through(run: Run, engine: Engine) -> None:
    broken = httpx.Response(200, content=b"{", headers={"content-type": "application/json"})
    script = Script(a=[broken], b=[completion(GOOD)])
    assert run(script) == Answer(answer=42)
    assert script.hosts() == ["a", "b"]
    assert [r.ok for r in rows(engine)] == [False, True]


def test_provider_without_key_is_skipped_without_a_row(run: Run, engine: Engine) -> None:
    script = Script(b=[completion(GOOD)])
    assert run(script, keys(a="")) == Answer(answer=42)
    assert script.hosts() == ["b"]
    assert [r.provider for r in rows(engine)] == ["b"]


def test_no_keys_at_all(run: Run, engine: Engine) -> None:
    script = Script()
    assert run(script, keys("", "", "")) is None
    assert script.requests == []
    assert rows(engine) == []


def test_has_any_key(engine: Engine) -> None:
    assert LlmChain(CONFIG, keys(a="", b=""), engine).has_any_key()
    assert not LlmChain(CONFIG, keys("", "", ""), engine).has_any_key()
    assert not LlmChain(CONFIG, keys("  ", "", ""), engine).has_any_key()


def test_all_fail_returns_none_with_a_row_per_call(run: Run, engine: Engine) -> None:
    script = Script(
        a=[httpx.Response(429)],
        b=[completion("nope"), completion("nope")],
        c=[httpx.ReadTimeout],
    )
    assert run(script) is None
    assert script.hosts() == ["a", "b", "b", "c"]
    logged = rows(engine)
    assert [r.provider for r in logged] == ["a", "b", "b", "c"]
    assert not any(r.ok for r in logged)
    assert all(r.error for r in logged)


def test_api_keys_never_stored_in_errors(run: Run, engine: Engine) -> None:
    echo_all = " ".join(KEYS.values())
    script = Script(
        a=[httpx.Response(401, json={"error": f"bad key {echo_all}"})],
        # the validation error quotes the reply, which here echoes the keys
        b=[completion(json.dumps({"answer": KEYS["b"]}))] * 2,
        c=[httpx.Response(500, text=echo_all)],
    )
    assert run(script) is None
    logged = rows(engine)
    assert len(logged) == 4
    for row in logged:
        assert row.error
        assert not any(key in row.error for key in KEYS.values())


def test_db_errors_are_not_swallowed(tmp_path: Path) -> None:
    unmigrated = make_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    client = httpx.Client(transport=httpx.MockTransport(Script(a=[completion(GOOD)])))
    try:
        with pytest.raises(OperationalError):
            LlmChain(CONFIG, keys(), unmigrated, client).complete_json(MESSAGES, Answer)
    finally:
        client.close()
        unmigrated.dispose()


def test_real_config_file() -> None:
    config = load_config()
    assert config.timeout_s == 8
    assert [p.name for p in config.providers] == ["groq", "cerebras", "gemini"]
    assert [p.key_env for p in config.providers] == [
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "GEMINI_API_KEY",
    ]
    assert all(p.base_url.startswith("https://") and p.model for p in config.providers)


def test_load_config_path_override(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        'timeout_s = 3\n[[providers]]\nname = "x"\nbase_url = "https://x.test"\n'
        'model = "m"\nkey_env = "GROQ_API_KEY"\n',
        encoding="utf-8",
    )
    assert load_config(path) == LlmConfig(
        3, (ProviderConfig("x", "https://x.test", "m", "GROQ_API_KEY"),)
    )


def test_provider_keys_default_env_file_is_repo_root() -> None:
    root = Path(__file__).resolve().parents[2]
    assert ProviderKeys.model_config.get("env_file") == root / ".env"


def test_provider_keys_read_env_and_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GROQ_API_KEY=from-file\nCEREBRAS_API_KEY=file-c\nKABTAK_TOKEN=t\n", encoding="utf-8"
    )
    monkeypatch.setenv("GROQ_API_KEY", "from-env")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")  # an empty variable must not hide the file
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    loaded = ProviderKeys(_env_file=env_file)
    assert loaded.get("GROQ_API_KEY") == "from-env"
    assert loaded.get("CEREBRAS_API_KEY") == "file-c"
    assert loaded.get("GEMINI_API_KEY") == ""


def test_keys_never_appear_in_repr(engine: Engine) -> None:
    provider_keys = keys()
    chain = LlmChain(CONFIG, provider_keys, engine)
    shown = " ".join(
        [
            repr(provider_keys),
            str(provider_keys),
            str(provider_keys.model_dump()),
            provider_keys.model_dump_json(),
            repr(chain),
            repr(vars(chain)),
        ]
    )
    assert not any(key in shown for key in KEYS.values())

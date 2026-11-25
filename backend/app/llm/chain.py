from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast

import openai
from pydantic import BaseModel, ValidationError
from sqlalchemy import Engine

from app.db.models import LlmCall
from app.db.session import session_scope
from app.llm.config import LlmConfig, ProviderConfig, ProviderKeys

if TYPE_CHECKING:
    import httpx  # dev dependency only; the SDK accepts these clients for tests

T = TypeVar("T", bound=BaseModel)

Messages = list[dict[str, str]]


class LlmChain:
    """Tries each configured provider in order until one returns JSON matching the schema."""

    def __init__(
        self,
        config: LlmConfig,
        keys: ProviderKeys,
        engine: Engine,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._engine = engine
        self._keys = keys  # stays masked; plaintext is read only to build clients and redact
        # providers without a key are skipped
        self._providers = [
            (
                p,
                openai.OpenAI(
                    api_key=keys.get(p.key_env),
                    base_url=p.base_url,
                    timeout=config.timeout_s,
                    max_retries=0,
                    http_client=cast(Any, http_client),
                ),
            )
            for p in config.providers
            if keys.get(p.key_env)
        ]

    def has_any_key(self) -> bool:
        return bool(self._providers)

    def complete_json(self, messages: Messages, schema: type[T]) -> T | None:
        """None when every provider fails. Database errors from call logging propagate."""
        for provider, client in self._providers:
            conversation = messages
            for _ in range(2):  # the call, then one repair
                started = time.perf_counter()
                try:
                    completion = client.chat.completions.create(
                        model=provider.model,
                        messages=cast(Any, conversation),
                        response_format={"type": "json_object"},
                    )
                # ValueError: a 200 whose body claims to be JSON and is not
                except (openai.APIError, ValueError) as exc:
                    self._log(provider, started, f"{type(exc).__name__}: {exc}")
                    break  # next provider

                try:
                    reply = completion.choices[0].message.content or ""
                except (AttributeError, IndexError, TypeError):  # SDK does not validate replies
                    reply = ""
                try:
                    result = schema.model_validate_json(reply)
                except ValidationError as exc:
                    self._log(provider, started, str(exc), completion)
                    conversation = [
                        *messages,
                        {"role": "assistant", "content": reply},
                        {
                            "role": "user",
                            "content": f"That reply failed validation:\n{exc}\n"
                            "Reply again with only the corrected JSON object.",
                        },
                    ]
                    continue
                self._log(provider, started, None, completion)
                return result
        return None

    def _log(
        self,
        provider: ProviderConfig,
        started: float,
        error: str | None,
        completion: object = None,
    ) -> None:
        latency_ms = round((time.perf_counter() - started) * 1000)
        if error is not None:
            # every configured key, not only this provider's: a reply can quote any of them
            for p, _ in self._providers:
                error = error.replace(self._keys.get(p.key_env), "***")
        usage = getattr(completion, "usage", None)
        with session_scope(self._engine) as session:
            session.add(
                LlmCall(
                    provider=provider.name,
                    model=provider.model,
                    latency_ms=latency_ms,
                    ok=error is None,
                    error=error,
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                    created_at=datetime.now(UTC),
                )
            )

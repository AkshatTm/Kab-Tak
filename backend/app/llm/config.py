import tomllib
from dataclasses import dataclass
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# shortcut: repo-relative paths; S4's packaged sidecar must pass its own locations
_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    model: str
    key_env: str


@dataclass(frozen=True)
class LlmConfig:
    timeout_s: float
    providers: tuple[ProviderConfig, ...]  # fallback order (ADR 0002)


def load_config(path: Path | None = None) -> LlmConfig:
    data = tomllib.loads((path or _ROOT / "config" / "llm.toml").read_text(encoding="utf-8"))
    return LlmConfig(data["timeout_s"], tuple(ProviderConfig(**p) for p in data["providers"]))


class ProviderKeys(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env", env_ignore_empty=True, extra="ignore"
    )

    groq_api_key: SecretStr = SecretStr("")
    cerebras_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")

    def get(self, key_env: str) -> str:
        """The key for an env-var name such as GROQ_API_KEY; empty when not configured."""
        key: SecretStr = getattr(self, key_env.lower())
        return key.get_secret_value().strip()

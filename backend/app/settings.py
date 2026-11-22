import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def default_db_url() -> str:
    # D1: %APPDATA%\KabTak\data.db; shortcut: non-Windows falls back to ~/.kabtak
    base = Path(os.environ.get("APPDATA") or Path.home() / ".kabtak")
    return f"sqlite:///{(base / 'KabTak' / 'data.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KABTAK_",
        env_file=Path(__file__).resolve().parents[2] / ".env",  # repo-root .env, optional
        extra="ignore",
    )

    token: str = ""  # empty token rejects every request
    db_url: str = ""
    port: int = 8765  # shortcut: unused until the S4 sidecar launcher reads it

    def resolved_db_url(self) -> str:
        return self.db_url or default_db_url()

# ADR 0001 — SQLite for local storage

**Status:** Accepted · 2026-11-22

## Context
The app is a Windows desktop app that will be installed by other people. Postgres was considered for
future growth, but it needs a separate server process on every user's machine and extra disk space.

## Decision
- Use **SQLite** (WAL mode) in `%APPDATA%\KabTak\data.db` (override with the `KABTAK_DB_URL` env var; tests always use a tmp DB), accessed through SQLModel with Alembic migrations.
- Keep the schema **Postgres-safe**: UUID text primary keys, UTC ISO-8601 timestamps, no SQLite-only types or functions in queries.

## Consequences
- Zero setup for users; backup = copy one file.
- If accounts/sync arrive later, Postgres goes on a **server**, and migration is mostly a connection-string change plus Alembic.
- Only one writer process (the sidecar) — fine for this app.

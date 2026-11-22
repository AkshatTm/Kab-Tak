# Kab Tak?

> It always takes longer than you think — even when you know it will.

Kab Tak logs your tasks, learns your estimation error per category from your own history, and tells you
when your day plan won't fit. Windows desktop app (Tauri 2 + React + Python sidecar + SQLite).

**Status:** planning done; scaffold (slice S0) not started. See [ROADMAP.md](ROADMAP.md) and [PROGRESS.md](PROGRESS.md).

## Docs
[SPEC.md](SPEC.md) (source of truth) · [ROADMAP.md](ROADMAP.md) · [RESEARCH.md](RESEARCH.md) · [docs/adr/](docs/adr) · [CLAUDE.md](CLAUDE.md)

## Run (available after S0)
```powershell
cp .env.example .env            # add free Groq / Cerebras / Gemini keys
cd backend; uv sync; uv run uvicorn app.main:app --reload
cd ui; npm ci; npm run dev
cargo tauri dev
```

License: MIT

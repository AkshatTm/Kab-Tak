# Kab Tak?

> It always takes longer than you think — even when you know it will.

Kab Tak logs your tasks, learns your estimation error per category from your own history, and tells you
when your day plan won't fit. Windows desktop app (Tauri 2 + React + Python sidecar + SQLite).

**Status:** scaffold (slice S0) in progress. See [ROADMAP.md](ROADMAP.md) and [PROGRESS.md](PROGRESS.md).

## Docs
[SPEC.md](SPEC.md) (source of truth) · [ROADMAP.md](ROADMAP.md) · [RESEARCH.md](RESEARCH.md) · [docs/adr/](docs/adr) · [CLAUDE.md](CLAUDE.md)

## Run
Needs uv, Node LTS, Rust and the Visual Studio Build Tools (C++ workload); install the Tauri CLI once with `cargo install tauri-cli --locked`.
```powershell
copy .env.example .env; copy ui\.env.example ui\.env   # add free Groq / Cerebras / Gemini keys
cd backend; uv sync; uv run uvicorn app.main:app --reload --port 8765   # needs KABTAK_TOKEN from .env
cd ui; npm ci; npm run dev
cargo tauri dev                                                          # from repo root
```

License: MIT

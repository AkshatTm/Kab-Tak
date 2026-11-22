# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S0 — Scaffold + GitHub (built, PR open, awaiting CI + your "merge")
- **Status:** done on branch `slice/S0-scaffold`; next is S1 (Data core, tag S) once S0 merges
- **Last commit:** see `git log -1` on `slice/S0-scaffold`
- **Open PR:** https://github.com/AkshatTm/Kab-Tak/pull/1
- **Next prompt:** after merge and `/clear`: "/resume" then "/slice S1" (Sonnet, stop after writing plans/S1.md)
- **Blockers / notes:** `/impeccable teach` must run before S2. API keys in `.env` before S2. After merge: move `plans/S0.md` to `plans/archive/`.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.

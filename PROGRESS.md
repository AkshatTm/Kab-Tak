# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S2 — Chat → task card (backend T1–T6 done, external review fixed; stopped at the provider check)
- **Status:** on `slice/S2-chat-card`: review fixes F1–F5, prompt examples (P1), bigger eval set with per-provider counts (P2). T7–T9 not started.
- **Last commit:** see `git log -1` on `slice/S2-chat-card`
- **Open PR:** #3, draft (do not merge: slice incomplete)
- **Next prompt:** after putting keys in `.env`: "/resume — S2: provider check (one raw json_object call per configured provider), then T7–T9. Stop before merge."
- **Blockers / notes:** NEEDS USER: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY` in the main folder's `.env` (all empty; one is enough to start, each provider can only be checked with its own key); then `/impeccable teach` (no `.impeccable.md`). The worktree has no `.env`; copy it there for live runs. Dev runs use a tmp `KABTAK_DB_URL`. S4 must bundle `parse_task.md` and `config/llm.toml`.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |
| S1 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #2 | pytest 81 passed (state machine, Hypothesis service model, migrations, API); ruff + mypy clean; tmp-DB lifecycle transcript, 409, restart keeps the running task; ui test/typecheck/lint/build green | Review fixed: backup never overwritten, FK off during migrations, 422 not 500 for bad PATCH/ids, estimate+parts frozen after first start, `now` sampled under the lock |
| S2 | Sonnet 5.5 (T2/T3/T4 via Sonnet subagents) | #3 draft | backend: pytest 256 passed, ruff + mypy clean, UI test/typecheck/lint green; live eval NOT run; UI not built | Eval gate is per field and overall; model ids from docs in `config/llm.toml`, never called |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- S1: SQLModel tables have no `relationship()` links, so the service flushes the parent row before children (FK order). Estimate and parts can only change before the first start (SPEC 1.6). `shortcut:` `list_tasks` filters by study day in Python; one process-wide lock for start/resume.
- Health version is the `app.__version__` constant (CI never installs the project). Lockfile must come from the CI npm (11.20); regenerate with `npx npm@11.20.0 install --package-lock-only`.
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.
- S2: the ADR 0004 guard matches the estimate against durations parsed from the text (`app/chat/durations.py`); bare numbers no longer count. The SPEC 1.3 sentence is both a prompt example and an eval row, so that row does not measure generalisation.

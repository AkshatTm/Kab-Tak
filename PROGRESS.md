# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S1 — Data core (built, PR open, awaiting CI + your "merge")
- **Status:** S0 merged (PR #1). S1 done on `slice/S1-data-core`: DB layer + migration with backup, timer state machine, task service, API routes, regenerated UI types.
- **Last commit:** see `git log -1` on `slice/S1-data-core`
- **Open PR:** https://github.com/AkshatTm/Kab-Tak/pull/2
- **Next prompt:** after merge and `/clear`: "/resume" then "/slice S2" (tag S, Opus only if the eval < 90%); stop after writing plans/S2.md. Before S2: run `/impeccable teach` and put real keys in `.env`.
- **Blockers / notes:** The harness forces a worktree for edits (CLAUDE.md says no worktrees); S1 was built in `.claude/worktrees/S1-plan`. Dev runs use a tmp `KABTAK_DB_URL`, never the real DB.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |
| S1 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #2 | pytest 81 passed (state machine, Hypothesis service model, migrations, API); ruff + mypy clean; tmp-DB lifecycle transcript, 409, restart keeps the running task; ui test/typecheck/lint/build green | Review fixed: backup never overwritten, FK off during migrations, 422 not 500 for bad PATCH/ids, estimate+parts frozen after first start, `now` sampled under the lock |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- S1: SQLModel tables have no `relationship()` links, so the service flushes the parent row before children (FK order). Estimate and parts can only change before the first start (SPEC 1.6). `shortcut:` `list_tasks` filters by study day in Python; one process-wide lock for start/resume.
- Health version is the `app.__version__` constant (CI never installs the project). Lockfile must come from the CI npm (11.20); regenerate with `npx npm@11.20.0 install --package-lock-only`.
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.

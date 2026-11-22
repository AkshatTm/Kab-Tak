# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S1 — Data core (planned; `plans/S1.md` written on Sonnet, awaiting approval)
- **Status:** S0 merged (PR #1, `8638a43`). S1 plan covers DB layer, timer state machine, services, API; T2 and T3 can run as parallel subagents.
- **Last commit:** see `git log -1` on branch `worktree-S1-plan` (plan only, not yet merged)
- **Open PR:** —
- **Next prompt:** "Approved. Build S1 from plans/S1.md on branch slice/S1-data-core: T1 inline, T2 and T3 as parallel subagents, then T4, T5, T6. Stop before merge."
- **Blockers / notes:** `/impeccable teach` must run before S2. API keys in `.env` before S2. Dev runs use a tmp `KABTAK_DB_URL`, never the real DB. The harness forces a worktree for edits even though CLAUDE.md says no worktrees; plan landed via branch `worktree-S1-plan`.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- Health version is the `app.__version__` constant (CI never installs the project). Lockfile must come from the CI npm (11.20); regenerate with `npx npm@11.20.0 install --package-lock-only`.
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.

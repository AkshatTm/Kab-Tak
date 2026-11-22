# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S2 — Chat → task card (planned; `plans/S2.md` written on Sonnet, awaiting approval)
- **Status:** S0 (PR #1) and S1 (PR #2) merged; S1 plan archived. S2 plan: backend T1–T6 first, UI after your checkpoints.
- **Last commit:** see `git log -1` on `slice/S2-chat-card` (plan only)
- **Open PR:** —
- **Next prompt:** "Approved. Build S2 from plans/S2.md on branch slice/S2-chat-card, backend tasks first (T2, T3, T4 as parallel subagents). Stop before merge." Before the UI tasks and the live eval: run `/impeccable teach` (DESIGN_BRIEF.md) and put real keys in `.env`.
- **Blockers / notes:** No `.impeccable.md` and no `.env` yet (your two checkpoints). The harness forces a worktree for edits (CLAUDE.md says no worktrees); work happens in `.claude/worktrees/S1-plan`. Dev runs use a tmp `KABTAK_DB_URL`. S4 must bundle `app/chat/prompts/parse_task.md`.

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

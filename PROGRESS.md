# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S2 — Chat → task card (backend T1–T6 done and reviewed; UI and live eval waiting on you)
- **Status:** on `slice/S2-chat-card`: LLM chain, chat parsing, eval set (36 sentences), `POST /chat` + `/corrections`. T7–T9 not started.
- **Last commit:** see `git log -1` on `slice/S2-chat-card`
- **Open PR:** draft PR for `slice/S2-chat-card` (do not merge: slice incomplete)
- **Next prompt:** after `/impeccable teach` and keys in `.env`: "/resume — continue S2 from T7 in plans/S2.md, then T9 (live eval). Stop before merge."
- **Blockers / notes:** NEEDS USER: `/impeccable teach` (no `.impeccable.md`) and at least one real key in `.env` (file exists, keys empty). Gemini `json_object` unconfirmed by docs: check in the eval. The worktree has no `.env`; copy it there for the live eval. Dev runs use a tmp `KABTAK_DB_URL`. S4 must bundle `parse_task.md` and `config/llm.toml`. Known gap: a lone-surrogate string in a hand-made request returns 500.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |
| S1 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #2 | pytest 81 passed (state machine, Hypothesis service model, migrations, API); ruff + mypy clean; tmp-DB lifecycle transcript, 409, restart keeps the running task; ui test/typecheck/lint/build green | Review fixed: backup never overwritten, FK off during migrations, 422 not 500 for bad PATCH/ids, estimate+parts frozen after first start, `now` sampled under the lock |
| S2 | Sonnet 5.5 (T2/T3/T4 via Sonnet subagents) | draft | backend: pytest 182 passed, ruff + mypy clean, tmp-DB fallback round trip; live eval NOT run; UI not built | Eval gate is per field and overall; model ids verified in `config/llm.toml` |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- S1: SQLModel tables have no `relationship()` links, so the service flushes the parent row before children (FK order). Estimate and parts can only change before the first start (SPEC 1.6). `shortcut:` `list_tasks` filters by study day in Python; one process-wide lock for start/resume.
- Health version is the `app.__version__` constant (CI never installs the project). Lockfile must come from the CI npm (11.20); regenerate with `npx npm@11.20.0 install --package-lock-only`.
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.

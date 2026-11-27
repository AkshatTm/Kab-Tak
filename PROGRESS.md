# PROGRESS

## Resume block
<!-- /resume reads this. /done rewrites it. Keep it short. -->
- **Current slice:** S2 — Chat → task card (built and verified; waiting for review and merge)
- **Status:** on `slice/S2-chat-card`: T1–T9 done, external review fixes F1–F5 and P1/P2 done, code review, ponytail review and Impeccable audit + polish done. Live eval passed.
- **Last commit:** see `git log -1` on `slice/S2-chat-card`
- **Open PR:** #3, ready for review (merge only when the user says "merge"; then move `plans/S2.md` to `plans/archive/`)
- **Next prompt:** after the merge: "/resume" then "/slice S3", stop after writing the plan.
- **Blockers / notes:** Groq and Gemini keys are in the main folder's `.env`; no Cerebras key (signup asks for payment details), so it is skipped and untested. The worktree has no `.env`. Free-tier rate limits fail back-to-back requests, so the live eval spaces them. Dev runs use a tmp `KABTAK_DB_URL`. S4 must bundle `parse_task.md` and `config/llm.toml`.

## Slice log
| Slice | Model used | PR | Result / evidence | Notes |
|---|---|---|---|---|
| S0 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #1 | pytest 8 passed; ruff + mypy clean; health 200/401; ui test/typecheck/lint/build green; clippy clean; screenshots `docs/screenshots/S0-health.png`, `S0-tauri.png` | Needed VS Build Tools (C++) for Rust; `beforeDevCommand` is `npm run dev` (Tauri runs it in `ui/`); `%APPDATA%\KabTak\data.db` created empty by a dev run |
| S1 | Sonnet 5.5 (T2/T3 via Sonnet subagents) | #2 | pytest 81 passed (state machine, Hypothesis service model, migrations, API); ruff + mypy clean; tmp-DB lifecycle transcript, 409, restart keeps the running task; ui test/typecheck/lint/build green | Review fixed: backup never overwritten, FK off during migrations, 422 not 500 for bad PATCH/ids, estimate+parts frozen after first start, `now` sampled under the lock |
| S2 | Sonnet 5.5 (T2/T3/T4 via Sonnet subagents; Sonnet review subagent) | #3 | pytest 280 passed; ruff + mypy clean; UI 47 tests, typecheck, lint, build green; live eval 99.4% overall, lowest field `parts` 95.9%, Groq answered all 49; screenshots `docs/screenshots/S2-*.png` | Review fixes: ADR 0004 value-matching guard, deadline, 422 for surrogates, focus stealing, lost input, offline pause, wheel rewriting the guess. Model ids in `config/llm.toml`; Groq and Gemini confirmed by live calls |

## Decisions made during build
<!-- Small decisions. Big ones get an ADR in docs/adr/. -->
- S1: SQLModel tables have no `relationship()` links, so the service flushes the parent row before children (FK order). Estimate and parts can only change before the first start (SPEC 1.6). `shortcut:` `list_tasks` filters by study day in Python; one process-wide lock for start/resume.
- Health version is the `app.__version__` constant (CI never installs the project). Lockfile must come from the CI npm (11.20); regenerate with `npx npm@11.20.0 install --package-lock-only`.
- `python -m app.openapi [path]` writes LF bytes (path arg avoids PowerShell `>` re-encoding); CI diffs `openapi.json` and `schema.ts`.
- Same linker failure happened twice (no MSVC Build Tools); stopped per rules, user installed them. Not a model escalation.
- S2: the ADR 0004 guard matches the estimate against durations parsed from the text (`app/chat/durations.py`); bare numbers no longer count. The SPEC 1.3 sentence is both a prompt example and an eval row, so that row does not measure generalisation.
- S2: the app is dark only for now (`shortcut:` in `ui/src/index.css`); `PRODUCT.md` is the design authority file that the installed Impeccable plugin writes.

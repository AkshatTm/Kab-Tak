# Kab Tak — CLAUDE.md

Kab Tak ("how long?") is a Windows desktop app that fixes time blindness: you chat a task plus your own
time guess, it times the work, learns your estimation error per category from your history, and later
shows a calibrated prediction (guess first, then reveal). Stack: Tauri 2 shell + React/Vite/TS UI + Python
FastAPI sidecar + SQLite. **SPEC.md is the source of truth; ADRs in `docs/adr/` record decisions.**
Order of work is in ROADMAP.md (slices S0–S11); state is in PROGRESS.md.

## Repo layout (created in S0)
```
backend/      uv project: app/{api,chat,llm,timer,calib,plan,db}, tests/
ui/           Vite + React + TS
src-tauri/    Tauri 2 (Rust)
config/llm.toml
plans/        current slice plan (plans/Sx.md); plans/archive/ = finished plans
docs/adr/     accepted architecture decisions
```

## Commands (PowerShell, run from repo root; finalised in S0)
```powershell
cd backend; uv run uvicorn app.main:app --reload     # backend
cd ui; npm run dev                                   # UI
cargo tauri dev                                      # desktop dev
cd backend; uv run pytest; cd ../ui; npm test        # all tests
cd backend; uv run ruff check .; uv run mypy .       # lint (py)
cd ui; npx tsc --noEmit; npx eslint .                # lint (ts)
cd src-tauri; cargo clippy -- -D warnings            # lint (rust)
cargo tauri build                                    # installer (needs PyInstaller sidecar, see S4)
```

## Hard rules
1. Never state or estimate how long any task, slice, phase or the project will take. No time bounds in plans, PRs or messages.
2. The LLM inside the app never predicts durations (ADR 0004).
3. Guess first, then reveal predictions (SPEC §1.6).
4. Never commit secrets. `.env` is git-ignored; `.env.example` lists `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`.
5. LLM provider order is fixed: Groq → Cerebras → Gemini (ADR 0002). Verify current model ids in provider docs before hardcoding.
6. SQLite with a Postgres-safe schema (ADR 0001). Schema changes only through Alembic.
7. Don't read `plans/archive/` unless asked.

## Plans
- `plans/IMPLEMENTATION_PLAN.md` — whole-project plan: workflow, **settled decisions D1–D18**, per-slice scope/tests/risks. Don't re-open a D-decision; if one is wrong, say so and propose a SPEC change.
- `plans/Sx.md` — the current slice's detailed plan, expanded from its section in IMPLEMENTATION_PLAN.md.

## Model policy
- **All coding is done by Sonnet 5.5.** Opus 5.5 only *plans*: slices tagged **O** in ROADMAP.md (S4, S7) get their `plans/Sx.md` written on Opus, then the user switches to `/model sonnet` to build.
- Escalate to Opus only when Sonnet hits the same failure twice or can't settle a design decision: stop, tell the user, and log it in PROGRESS.md.
- Record the model used per slice in PROGRESS.md.

## Session protocol
- **Start:** `/resume` (read Resume block in PROGRESS.md, run tests, report state).
- **Plan:** `/slice Sx` → `plans/Sx.md` (bite-sized tasks, exact files, tests first, evidence). Wait for approval.
- **Build:** on branch `slice/Sx-name`. TDD for all logic (`superpowers:test-driven-development`). Independent tasks → `superpowers:subagent-driven-development`; small/coupled work inline.
- **Debug:** `superpowers:systematic-debugging` before any fix.
- **Verify:** `superpowers:verification-before-completion` — evidence, not claims: test output, commands with results, Playwright screenshots → `docs/screenshots/`.
- **Review:** code-review subagent (`superpowers:requesting-code-review`) for correctness, then `/ponytail-review` for bloat; UI slices also `/impeccable audit` then `/impeccable polish`.
- **End:** `/done`, then the user runs `/clear`.

## Git workflow
- `main` is always green. One branch per slice: `slice/S1-data-core`.
- Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`), small commits.
- Push branch, `gh pr create` (body: what changed, evidence, how to demo), wait for CI, then
  `gh pr merge --squash --delete-branch` **only after the user says "merge"**.
- Repo: https://github.com/AkshatTm/Kab-Tak

## Spec changes
Edit SPEC.md + add a CHANGES.md entry. Never create new PRD/design docs. New big decisions → new ADR.

## Coding conventions
- **Python:** type hints everywhere, ruff + mypy clean, Pydantic models for all API I/O, no business logic in route functions.
- **TypeScript:** strict mode, no `any`.
- **Rust:** clippy clean.

## Skills / plugins (and overrides)
- **Superpowers:** as in the session protocol. Overrides: skip `brainstorming` (SPEC is done); `writing-plans` saves to `plans/Sx.md`; `finishing-a-development-branch` never merges (git workflow above); no worktrees.
- **Impeccable** is the single design authority (`.impeccable.md`, from `/impeccable teach` + DESIGN_BRIEF.md). `frontend-design` only sets the direction in S2, inside Impeccable's context. `taste-skill` only for an optional landing page in S11.
- **Ponytail** is always on: smallest complete change, `shortcut:` comments for known limits; `/ponytail-debt` + `/ponytail-audit` before S11.
- No Handoff plugin: `/done` + PROGRESS.md is the handoff.

## Data safety
The user dogfoods from S3 on; dev uses the real `%APPDATA%\KabTak\data.db`. Tests always use a tmp DB.
Never delete or reset that file; migrations back it up first (D2).

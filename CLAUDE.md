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

## Model policy
Sonnet 5.5 does all work by default. Opus 5.5 only for slices tagged **O** in ROADMAP.md, or when Sonnet
hits the same failure twice / can't settle a design decision. Record the model used per slice in PROGRESS.md.

## Session protocol
- **Start:** `/resume` (read Resume block in PROGRESS.md, run tests, report state).
- **Plan:** `/slice Sx` → plan mode → `plans/Sx.md` (tasks, files touched, tests, evidence). Wait for approval.
- **Build:** TDD for all logic (failing test first). Subagent-driven execution for independent tasks to keep main context small.
- **Verify:** evidence, not claims — test output, commands with results, Playwright screenshots for UI.
- **Review:** separate review subagent for correctness, then `/ponytail-review` for bloat; UI slices also `/impeccable audit` then polish.
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

## Skills / plugins in use
Superpowers (systematic-debugging etc.), Impeccable (design; context in `.impeccable.md`), Ponytail
(`/ponytail-review`), Handoff, taste-skill, Anthropic `frontend-design`. Use them as the session protocol says.

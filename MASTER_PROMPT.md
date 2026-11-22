# Master prompt for Claude Code

How to use:
1. Put this whole folder in an empty project folder, e.g. `D:\Projects\kab-tak\` (keep `docs/adr/` as is).
2. Open Claude Code in that folder. Run `/model sonnet` (Sonnet 5.5).
3. Copy everything between the START and END markers below and send it as your first message.

==================== ▼ START COPYING HERE ▼ ====================

You are starting a new project called **Kab Tak** in this folder. All the planning is already
done. Read these files fully before doing anything else:

- `SPEC.md` — the living spec and single source of truth (product, architecture, data/API contract, non-goals)
- `ROADMAP.md` — ordered vertical slices S0–S11 with model tags and demo/evidence criteria
- `RESEARCH.md` — why the design looks like this
- `DESIGN_BRIEF.md` — input for `/impeccable teach`
- `docs/adr/0001` … `0005` — accepted architecture decisions
- `PROGRESS.md`, `CHANGES.md` — state tracking files

Environment: Windows 11, PowerShell, Python via **uv**, Node LTS, Rust stable, Tauri 2 prerequisites
(WebView2, MSVC build tools). GitHub user: **AkshatTm**. The GitHub CLI (`gh`) is available.

## Your tasks for this session (in order — stop after step 6)

### 1. Write `CLAUDE.md` (project root, at most ~120 lines)
Keep it short and operational. Point to SPEC.md instead of copying it. It must contain:
- **One-paragraph project summary** + "SPEC.md is the source of truth; ADRs record decisions."
- **Repo layout** you will create in S0:
  `backend/` (uv project: `app/api, app/chat, app/llm, app/timer, app/calib, app/plan, app/db`, `tests/`),
  `ui/` (Vite React TS), `src-tauri/` (Tauri 2), `config/llm.toml`, `plans/`, `plans/archive/`, `docs/adr/`.
- **Commands** (PowerShell): run backend, run UI, run Tauri dev, run all tests, lint, build installer.
- **Hard rules:**
  1. Never state or estimate how long any task, slice, phase or the project will take. No time bounds in plans, PRs or messages.
  2. The LLM inside the app never predicts durations (ADR 0004).
  3. Guess first, then reveal predictions (SPEC §1.6).
  4. Never commit secrets. `.env` is git-ignored; `.env.example` lists `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`.
  5. LLM provider order is fixed: Groq → Cerebras → Gemini (ADR 0002). Verify current model ids in provider docs before hardcoding.
  6. SQLite with a Postgres-safe schema (ADR 0001). Schema changes only through Alembic.
  7. Don't read `plans/archive/` unless asked.
- **Model policy:** Sonnet 5.5 does all work by default. Opus 5.5 only for slices tagged **O** in ROADMAP.md, or when Sonnet hits the same failure twice / can't settle a design decision. Record which model was used per slice in PROGRESS.md.
- **Session protocol:**
  - Start: `/resume` (read the Resume block in PROGRESS.md, run tests, report state).
  - Plan: plan mode → save the plan to `plans/Sx.md` (tasks, files touched, tests to write, evidence to collect). Wait for my approval.
  - Build: TDD for all logic (write the failing test first). Use subagent-driven execution for independent tasks so the main context stays small.
  - Verify: show evidence, not claims — test output, commands run with their results, screenshots for UI (Playwright).
  - Review: a separate review subagent for correctness, then `/ponytail-review` for bloat; UI slices also `/impeccable audit` then polish.
  - End: `/done`, then I run `/clear`.
- **Git workflow:**
  - `main` is always green. One branch per slice: `slice/S1-data-core`.
  - Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`), small commits.
  - Push the branch, open a PR with `gh pr create` (body: what changed, evidence, how to demo), wait for CI, then squash-merge with `gh pr merge --squash --delete-branch` **only after I say "merge"**.
- **Spec changes:** edit SPEC.md + add a CHANGES.md entry. Never create new PRD/design docs. New big decisions → new ADR.
- **Coding conventions:** Python — type hints everywhere, ruff + mypy clean, Pydantic models for all API I/O, no business logic in route functions. TS — strict mode, no `any`. Rust — clippy clean.

### 2. Create project slash commands in `.claude/commands/`
- `resume.md` — read PROGRESS.md Resume block + current `plans/Sx.md`, run `git status`, run the test suite, report: current slice, status, failing tests, next step. Remind me which model the slice is tagged for.
- `slice.md` — takes a slice id (e.g. `S3`): read its ROADMAP row + relevant SPEC sections, enter plan mode, write `plans/Sx.md`.
- `done.md` — update PROGRESS.md (Resume block + slice log + model used + evidence), commit, push, open/update the PR, move the finished plan to `plans/archive/` after merge, and print the exact next prompt for me to paste after `/clear`.

### 3. Repo basics
- `git init` (if needed), `.gitignore` (Python, Node, Rust/Tauri, `.env`, `*.db`, `dist/`, `target/`, PyInstaller output), `.env.example`, `README.md` (short: what it is, status, how to run), `LICENSE` (MIT).
- `.github/workflows/ci.yml` on `windows-latest`: uv sync + ruff + mypy + pytest; npm ci + tsc + eslint + vitest. (Tauri build job can be added in S4.)

### 4. GitHub
- Check `gh auth status`. If not logged in, stop and tell me to run `gh auth login`.
- Create the repo: `gh repo create AkshatTm/kab-tak --public --source . --remote origin`
  (ask me first if I want it private instead).
- First commit on `main`: `chore: project docs and Claude setup` containing all docs, CLAUDE.md, commands, CI. Push.

### 5. Design context
- Tell me to run `/impeccable teach` with `DESIGN_BRIEF.md` as the input, so `.impeccable.md` is created. (Don't fake its output.)

### 6. Plan S0
- Enter plan mode and write `plans/S0.md` for **S0 Scaffold + GitHub** following the ROADMAP row and the CLAUDE.md protocol.
- Update the PROGRESS.md Resume block.
- **Stop and wait for my approval.** Don't start building S0 in this session.

When you report back, list: files created, the GitHub repo URL, CI status, and the exact next prompt for me.

==================== ▲ STOP COPYING HERE ▲ ====================

## Prompt for each later slice (paste after `/clear`)

==================== ▼ START COPYING HERE ▼ ====================
/resume
Then run /slice S<number>. Use the model tag from ROADMAP.md. Stop after writing the plan and wait for my approval.
==================== ▲ STOP COPYING HERE ▲ ====================

---
description: Resume work — read PROGRESS.md, check repo and tests, report state
---
1. Read the Resume block in `PROGRESS.md` and the current `plans/Sx.md` it points to (if any).
2. Run `git status` and `git log --oneline -5`.
3. Run the test suite (backend `uv run pytest`, UI `npm test` — skip parts that don't exist yet and say so).
4. Report concisely: current slice, status, failing tests, next step.
5. Remind me which model the slice is tagged for in ROADMAP.md (S = Sonnet 5.5, O = Opus 5.5) and whether the current session model matches.
Do not state or estimate durations.

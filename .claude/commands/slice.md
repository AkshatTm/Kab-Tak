---
description: Plan a slice — /slice S3
argument-hint: <slice id, e.g. S3>
---
Plan slice **$ARGUMENTS**.
1. If `plans/$ARGUMENTS.md` already exists (Opus may have written it), read it, check it against the current code, and report gaps instead of rewriting it.
2. Otherwise read: its section in `plans/IMPLEMENTATION_PLAN.md` (including the D-decisions it cites), its ROADMAP.md row, and only the SPEC.md / ADR sections it touches.
3. Model check: if the slice is tagged **O** and this session isn't Opus, tell me to switch to Opus for planning and stop.
4. Write `plans/$ARGUMENTS.md` using `superpowers:writing-plans` style: goal, branch `slice/$ARGUMENTS-<name>`, ordered bite-sized tasks with exact files (mark independent ones for subagents), the tests to write first for each, evidence to collect, review steps, out-of-scope.
5. No time estimates anywhere. Stop and wait for my approval.

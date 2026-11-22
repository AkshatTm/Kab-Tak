---
description: Plan a slice — /slice S3
argument-hint: <slice id, e.g. S3>
---
Plan slice **$ARGUMENTS**.
1. Read its row in `ROADMAP.md` and only the SPEC.md / ADR sections relevant to it.
2. Check the slice's model tag; if it is **O** and the session isn't Opus, tell me to switch before planning.
3. Enter plan mode and write `plans/$ARGUMENTS.md`: goal, tasks (ordered, independent ones marked for subagents), files touched, tests to write first (TDD), evidence to collect, review steps, branch name `slice/$ARGUMENTS-<name>`.
4. No time estimates anywhere. Stop and wait for my approval.

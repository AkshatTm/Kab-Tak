---
description: Close out the current slice session
---
1. Update `PROGRESS.md`: rewrite the Resume block, add/update the slice log row (model used, PR, evidence, notes).
2. Commit (Conventional Commits), push the branch, open or update the PR with `gh pr create` / `gh pr edit` (what changed, evidence, how to demo). End the PR body with the attribution line from the session reminder.
3. Do NOT merge until I say "merge". After merge: move `plans/Sx.md` to `plans/archive/` and commit.
4. Print the exact next prompt for me to paste after `/clear`:
   `/resume` then `/slice S<next>`, using the model tag from ROADMAP.md, stopping after writing the plan.
No time estimates anywhere.

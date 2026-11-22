# Kab Tak — Roadmap (vertical slices)

Rules
- Every slice is something a user can do end to end, with a **demo** at the end.
- **No time estimates anywhere.** Slices have an order, not a duration.
- Model tag: **S** = Sonnet 5.5 (default). **O** = Opus 5.5, only where noted. If Sonnet gets stuck on a
  slice (same failure twice, or a design decision it can't settle), escalate that sub-task to Opus and note it in PROGRESS.md.
- Each slice: `/resume` → plan mode → `plans/Sx.md` → execute → tests + evidence → review subagent → `/done`.

| Slice | Tag | What the user can do | Demo / evidence |
|---|---|---|---|
| **S0 Scaffold + GitHub** | S | Clone the repo and run backend, UI and Tauri dev with one command each | `uv run pytest` green, `GET /api/health` 200, Vite page loads, `cargo tauri dev` opens a window, GitHub repo exists with CI passing on `main` |
| **S1 Data core** | S | Create, start, pause, resume, stop a task through the API | pytest for the timer state machine (incl. Hypothesis: active ≤ wall, never two running), Alembic migration, curl transcript |
| **S2 Chat → task card** | S (O for prompt + schema design if eval < 90%) | Type the "Video 2…" sentence in the browser chat, see a parsed card, edit and confirm | Eval set of ≥ 25 sample sentences (`tests/fixtures/chat_eval.jsonl`) with ≥ 90% field accuracy; provider fallback test with mocked 429s; screenshot |
| **S3 Chat-driven timer + Today view** | S | "start" / "break" / "back" / "done" in chat; Done/Partly/Stuck; Today list with guess vs actual | Playwright test of the full loop; fast-path commands make zero LLM calls (asserted) |
| **S4 Windows desktop shell** | O | Install and run as a desktop app: tray, mini timer, overrun "Still on it?", forgotten-timer recovery on launch | PyInstaller sidecar builds; `cargo tauri build` produces an installer; screenshots of tray + mini timer; recovery test |
| **S5 Observation dashboard + shadow Level A** | S | See per-category guess vs actual and "Learning DSA (3/5)"; shadow predictions stored | Unit tests for shrinkage maths; `predictions.shown=false` rows created in observation mode; screenshot |
| **S6 Prediction mode (guess-first reveal)** | S | After observation ends, type a guess → see calibrated time + range + last 5 similar tasks | Test that prediction is never returned before an estimate exists; screenshot |
| **S7 Level B content rates + Level C blend + backtest** | O | See learned rates ("1 lecture-min ≈ 1.8 min") and a blended prediction | Walk-forward backtest report (markdown) on real + synthetic data; NNLS property tests |
| **S8 Insights** | S | Bias by category, gut-error trend, interval coverage, model vs gut | Metrics unit-tested against hand-computed fixtures; screenshot |
| **S9 Plan check** | S | Paste tonight's tasks + available hours → realistic total, P(fit), what to drop | Monte Carlo seeded tests; screenshot |
| **S10 Retro log + idle detection + export** | S | "I did CN unit 1 for ~40 min"; idle keep/discard/split; export JSON/CSV | Tests + screenshot of idle dialog |
| **S11 Ship for others** | S (O for signing/updater issues) | First-run onboarding with API-key setup (stored in Credential Manager), signed installer, GitHub Release, auto-update | Fresh Windows user profile install walkthrough; release artifact on GitHub |

After S11: update SPEC.md for Phase 2 (Brain Dump) — don't create a new doc set.

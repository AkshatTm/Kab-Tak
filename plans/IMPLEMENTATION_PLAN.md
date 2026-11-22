# Kab Tak — Implementation plan (whole project)

Written by Opus 5.5 as the cross-slice plan. **SPEC.md stays the source of truth for behaviour.** This file
holds the *how*: build order, the decisions Sonnet should not re-open, tests, evidence and risks per slice.
`/slice Sx` reads the matching section here and expands it into `plans/Sx.md`.

No durations anywhere — slices have an order, not a length.

---

## 0. Workflow (every slice)

```
/clear → /resume → /slice Sx → plan approved → branch slice/Sx-name → build (TDD) → verify → review → /done → "merge"
```

| Step | What happens | Skill / tool |
|---|---|---|
| Plan | `/slice Sx` expands this file's section into `plans/Sx.md` (bite-sized tasks, exact files, tests first). O-tagged slices: plan on **Opus**, then `/model sonnet` to build | `superpowers:writing-plans` (save to `plans/Sx.md`, not its default folder) |
| Build | One task at a time, failing test first. Independent tasks with separate files → subagents; small or coupled slices → do them inline | `superpowers:test-driven-development`, `superpowers:subagent-driven-development` |
| Bug | Any red test or odd behaviour → root cause before a fix. **Same failure twice → stop, tell the user to escalate that sub-task to Opus**, log it in PROGRESS.md | `superpowers:systematic-debugging` |
| Verify | Run the commands, paste the output. UI → Playwright screenshot to `docs/screenshots/Sx-*.png` | `superpowers:verification-before-completion` |
| Review | 1) code-review subagent for correctness against SPEC 2) `/ponytail-review` for bloat 3) UI slices: `/impeccable audit` → fix → `/impeccable polish` | `superpowers:requesting-code-review`, `ponytail:ponytail-review`, `impeccable:impeccable` |
| Close | `/done` (PROGRESS, PR, next prompt). Merge only on "merge" | `.claude/commands/done.md` |

Skill overrides (these beat the skills' defaults):
- `superpowers:brainstorming` — **skip**; product design is done (SPEC + ADRs). Use it only for a genuinely new feature the user asks for.
- `superpowers:finishing-a-development-branch` — don't take its merge/discard options; follow the CLAUDE.md git flow.
- `superpowers:using-git-worktrees` — not needed; one slice at a time.
- Design authority is **Impeccable** (`.impeccable.md`). `frontend-design` is used once, in S2, to set the aesthetic direction inside the Impeccable context. `taste-skill` targets marketing sites, so it's used only for the optional landing page in S11. Never let two design skills fight over the same screen.
- Ponytail mode stays on: the smallest change that fully works, and a `shortcut:` comment for known limits. `/ponytail-debt` before S11.

User checkpoints (things only you can do):
| Before | You do |
|---|---|
| S2 | Run `/impeccable teach` with DESIGN_BRIEF.md (→ `.impeccable.md`). Put real keys in `.env` |
| S3 merged | **Start dogfooding daily** in the browser build. S5–S7 need your real data |
| S7 | Have ≥ ~30 real done tasks if possible (synthetic data covers the rest) |
| S11 | Decide on code signing (see S11) |

---

## 1. Global decisions (settled — fold into SPEC/ADRs in the slice noted)

| # | Decision | Where it goes / when |
|---|---|---|
| D1 | Data dir `%APPDATA%\KabTak\` (fix ADR 0001's old `TimeCalibrator` path). Dev uses the **same** DB file by default so dogfooding data is real. Tests always use a tmp DB. `KABTAK_DB_URL` env overrides | ADR 0001 + SPEC §2.1, S0 |
| D2 | **Before every Alembic upgrade at startup, copy `data.db` → `data.db.bak-<rev>`.** Migrations must never drop user data | SPEC §2.1, S1 |
| D3 | IDs: `str(uuid4())` text PKs. Timestamps: one small `UTCDateTime` SQLAlchemy TypeDecorator (aware UTC in, aware UTC out). API emits ISO-8601 with `Z` | S1 |
| D4 | **Study day** = local day with a cutoff, setting `day_starts_at` (default `04:00`). A task at 00:30 belongs to the previous day. The backend uses the OS local timezone (it's a local sidecar). `GET /tasks?date=` uses the study day | SPEC §3.3 + settings, S1 |
| D5 | Backend owns timer state. `pause` / `stop` accept an optional `at` (≤ now, ≥ the open session's start), needed for idle discard and forgotten-timer recovery. Elapsed time in the UI = server `started_at` of the open session + local clock, and it re-syncs from `GET /tasks/running` | SPEC §3.3, S1 |
| D6 | "Only one running": `start` returns **409** with the running task's id. The UI asks pause/stop, then retries. Enforced in the service layer inside one transaction (no DB trick), proven with a Hypothesis test | S1 |
| D7 | Task status: created **with** an estimate → `ready`; without → `draft` (can't start). Parsed cards aren't persisted until confirmed | S1/S2 |
| D8 | Chat history isn't persisted in Phase 1 (`shortcut:` — the UI keeps it in memory; the `events` table is the audit log). Fast-path commands resolve their target from the DB: `start` → latest `ready` task, `break/back/done` → the running/paused task | SPEC §2.4, S3 |
| D9 | **Predictions are made inside task creation** (and again only if the estimate is edited before the first start), one row per available level, `shown` decided by mode. **Remove `POST /predict`** from SPEC. Plan check doesn't store predictions (they're aggregates with no task). Guess-first holds because the estimate is part of the create request | SPEC §1.6/§3.3, S5 |
| D10 | `installed_at` setting written on first DB init. It starts the observation clock | S1 |
| D11 | API types: backend dumps OpenAPI (`uv run python -m app.openapi > ui/src/api/openapi.json`); UI generates types with `openapi-typescript`. CI regenerates and fails on diff. No hand-written API types | S0 wiring, S1 first use |
| D12 | Auth from S0: middleware checks `X-KabTak-Token`. Dev token comes from `.env` (`KABTAK_TOKEN`) and Vite env. Release: Rust generates a token per launch and passes it to the sidecar via env and to the UI via a Tauri command. CORS allows only `http://localhost:5173` and `http://tauri.localhost` | S0, S4 |
| D13 | Sidecar handshake: Python binds port 0, prints `KABTAK_READY port=<n>` to stdout. Rust reads it (no port race). The Python entry point runs `uvicorn.run(app)` programmatically (PyInstaller-safe) and runs Alembic programmatically with the bundled `migrations/` dir | S4 |
| D14 | LLM: the `openai` SDK with per-provider `base_url`, `response_format={"type":"json_object"}`, Pydantic validation, one repair retry, then the next provider. Live LLM tests are marked `@pytest.mark.live` and CI runs `-m "not live"` | S2 |
| D15 | UI: React + TS strict, Tailwind v4 (`@tailwindcss/vite`), TanStack Query for server state, plain `fetch` wrapper, **no router** (tab state). Mini timer = second Vite entry `mini.html`. Recharts only from S8 | S0/S2/S4 |
| D16 | Python pinned to **3.12** (`.python-version`) for PyInstaller/scipy wheel safety. Node LTS. Tauri CLI via `cargo install tauri-cli --locked` (`cargo tauri …` from repo root; `beforeDevCommand: npm --prefix ui run dev`) | S0 |
| D17 | API keys: env var wins, otherwise Windows Credential Manager via `keyring` (service `KabTak`). `PUT /settings` writes to keyring and never returns a key, only `{provider: configured: bool}` | S11 (env-only until then) |
| D18 | Screenshots for evidence are committed to `docs/screenshots/` (small PNGs; reused in the README) | S2+ |

Handoff plugin: **not used.** `/done` + the PROGRESS.md Resume block is the handoff. A second mechanism would conflict.

---

## 2. Slices

### S0 Scaffold + GitHub — S
Detailed plan: `plans/S0.md`.

### S1 Data core — S
**Goal:** create / start / pause / resume / stop a task through the API, with data that survives restart.
- `app/db`: SQLModel tables from SPEC §3.1 (all of them now, so later slices don't need a migration storm), engine with WAL + `foreign_keys=ON`, `UTCDateTime`, first Alembic migration + seed data (part types, categories, `installed_at`, defaults for settings). Backup-before-upgrade (D2).
- `app/timer`: pure state machine module (no DB) + a service that persists sessions. Rules D5, D6, D7. Computes `active_min` (Σ sessions) and `wall_min` on stop.
- `app/api`: `/tasks` CRUD, start/pause/resume/stop (`at` optional), `GET /tasks?date=` (D4), `GET /tasks/running`. Pydantic in/out models separate from tables. Route bodies only call services.
- `events` row for every state change.
- **Tests first:** state machine transitions (table-driven); Hypothesis: random command sequences ⇒ active ≤ wall, never two open sessions, sessions don't overlap; `at` validation; study-day boundary at 03:59 vs 04:00; migration up from empty + backup file created; API tests via `httpx`/TestClient.
- **Evidence:** pytest output, `alembic upgrade head` on a fresh DB, a curl (`Invoke-RestMethod`) transcript of the full lifecycle.
- **Risk:** SQLite timezone round-trips → D3 test that writes and reads back an aware datetime.

### S2 Chat → task card — S (Opus if the eval < 90% after one prompt iteration)
**Goal:** type the "Video 2…" sentence in the browser, see a parsed card, edit, confirm.
- Before coding: verify current model ids and OpenAI-compat base URLs for Groq, Cerebras, Gemini in their docs. Write `config/llm.toml` with the verified ids and today's date in a comment.
- `app/llm`: provider chain (D14), timeout 8 s, fallthrough on 429 / 5xx / timeout / invalid JSON after one repair. Every call → `llm_calls`.
- `app/chat`: `prompts/parse_task.md` (explicitly forbids inventing durations; `estimate_min` only from the user's words), schema from SPEC §3.2, few-shot from the latest 10 `corrections`. `POST /chat` returns the intent + card. Editing a card before confirm stores a `corrections` row.
- UI: design pass first (`frontend-design` direction within `.impeccable.md`), then the chat screen + editable task card (category chip, parts with quantities, estimate required to start, Enter to confirm).
- **Tests first:** chain fallthrough with a mocked client (429 → next, timeout → next, bad JSON → repair → next, all fail → empty card + message); schema validation; "no estimate in text ⇒ `estimate_min` null" (ADR 0004) on recorded responses; corrections stored; Vitest for the card's edit/confirm logic.
- **Eval:** `backend/tests/fixtures/chat_eval.jsonl` with ≥ 25 sentences (include Hinglish, multi-task, tentative, no-estimate). `uv run pytest -m live tests/test_chat_eval.py` prints field-level accuracy. Gate ≥ 90%. The report goes in the PR body.
- **Evidence:** eval report, fallback test output, screenshot.

### S3 Chat-driven timer + Today view — S
**Goal:** run the whole loop from chat; the Today list shows guess vs actual. **Dogfooding starts after this merges.**
- Fast-path parser (pure function, zero LLM): `start | shuru`, `break | pause | ruko`, `back | resume`, `done | stop | ho gaya`, `stuck`, `partly`, `undo`, `today` (case- and punctuation-insensitive). `undo` reverts only the last timer event (within the current session).
- Outcome step after stop: single keys D / P / S. Partly → free text → LLM `stop_with_outcome` → updates parts' `completed_qty` (confirm card).
- Running-task banner; 409 handling (D6); Today screen (guess, actual, ratio, outcome; study day D4).
- **Tests first:** fast-path table test incl. Hinglish; an assertion that fast-path commands make **zero** LLM calls (spy on the client); undo cases; Playwright e2e of the full loop (Playwright `webServer` boots uvicorn on a tmp DB + Vite; the LLM is mocked through a `KABTAK_LLM_FAKE=1` fixture responder, `shortcut:` test-only).
- CI: add a Playwright job.
- **Evidence:** Playwright run + screenshots of chat loop and Today.

### S4 Windows desktop shell — **O** (Opus plans, Sonnet builds)
**Goal:** install and run as a desktop app with tray, mini timer, overrun check-in, forgotten-timer recovery.
- PyInstaller one-file sidecar (`backend/kabtak.spec`, bundles `migrations/` and `config/`), named per Tauri's target-triple rule, under `src-tauri/binaries/` (git-ignored, built by a script).
- Rust: spawn the sidecar via `tauri-plugin-shell`, read `KABTAK_READY` (D13), pass the token (D12), restart on crash, kill on exit. Expose `get_backend_info` to the UI. Tray (show / mini timer / quit), a mini timer window (always on top, `mini.html`), notifications (`tauri-plugin-notification`).
- F5 overrun: when active time ≥ estimate → notification + in-app "Still on it?" (keep going / done / stuck); the timer keeps counting.
- F6 recovery: on launch, if a task is running → "Were you still working? Stop at ___" (default = the last known activity, editable) → `stop` with `at`.
- CI: `cargo clippy -D warnings` on PRs; `tauri-apps/tauri-action` build on `main` only.
- **Tests first:** recovery decision logic (backend/UI unit); sidecar handshake parse (Rust unit test); a smoke script that launches the built sidecar exe and calls `/api/health`.
- **Evidence:** the installer file produced, screenshots of tray + mini timer + recovery dialog, smoke output.
- **Risks:** PyInstaller hidden imports (uvicorn, sqlalchemy dialects, alembic) → keep an explicit list. AV false positives on one-file exes → fall back to one-dir if Defender flags it. Leftover zombie sidecar → Job Object or kill on `RunEvent::Exit`.

### S5 Observation dashboard + shadow Level A — S
- `app/calib/level_a.py`: pure functions, SPEC §3.4 Level A exactly (weights, clipping, shrinkage k = 3, prior ln 1.5, pooled residual quantiles when n < 15).
- Mode logic: observation if `now − installed_at < 7d` OR category done-count < 5 (both settings) (ADR 0005).
- Prediction creation inside task create (D9), `shown = false` in observation, `model_version = "A-1"`. Update SPEC to remove `/predict`.
- `GET /calibration`; UI "Learning DSA (3/5)" progress + estimate-vs-actual per category.
- **Tests first:** shrinkage against hand-computed fixtures (no data → prior; one category → pulled toward global); weighted quantiles; recency weights; retro weight 0.5; stuck excluded; mode switching at the boundaries; prediction rows created on create with `shown=false`.

### S6 Prediction mode (guess-first reveal) — S
- Create response includes the shown prediction when the category is in prediction mode; the card reveals "Likely 2h 20m (2h–2h 50m)" + last 5 similar tasks (same category, most recent done) **only after** the estimate field is filled and confirmed.
- Every number has a tooltip with how it was computed (DESIGN_BRIEF).
- **Tests first:** API never returns a prediction for a draft without an estimate; reveal component renders nothing before the estimate (Vitest); Playwright: guess → reveal.

### S7 Level B + Level C + backtest — **O** (Opus plans, Sonnet builds)
- `level_b.py`: weighted NNLS (`scipy.optimize.nnls` on √w-scaled rows), intercept c₀ ≥ 0, activation rule from SPEC; `completed_qty` for partly.
- `level_c.py`: inverse-variance α from walk-forward log errors over the last 30 eligible tasks; residual quantile range.
- `backtest.py`: walk-forward (strictly past data per task), metrics from SPEC §3.4. CLI `uv run python -m app.calib.backtest --data real|synthetic` → markdown report.
- Synthetic generator with known true rates/bias (seeded) to prove recovery.
- **Tests first:** NNLS property tests (non-negative rates; recovers known rates on noiseless synthetic data); no-leakage test (perturbing a future task doesn't change past predictions); α → 1 when B is absent; coverage near 80% on synthetic data.
- **Evidence:** backtest report on synthetic + real data in the PR body.

### S8 Insights — S
- `GET /insights?range=` returns: bias per category, gut-error trend (rolling median |r|), 80% interval coverage (from stored `predictions`, the honest record), model vs gut %. Recharts screen.
- **Tests first:** every metric against a hand-computed fixture.

### S9 Plan check — S
- `app/plan/monte_carlo.py`: 2,000 samples per task with ε from category residuals, transition buffer (setting, 5 min), median + p80 total, P(fit), drop suggestion (low priority, widest interval). Tentative tasks are excluded (SPEC §1.6 rule 5).
- Chat intent `plan_check` (LLM parses the list) → `POST /plan/check` → screen.
- **Tests first:** seeded RNG ⇒ deterministic output; one task with zero residual variance ⇒ P(fit) is 0 or 1; buffer counted (n−1) times; tentative excluded.

### S10 Retro log + idle detection + export — S
- Retro: intent `retro_log` → card → task with `source=retro`, `active_min` set, no sessions, weight 0.5 in calibration.
- Idle (F16): Rust polls `GetLastInputInfo` (`windows` crate). After N min (setting) with a task running, it emits a `idle-detected {idle_since}` event → dialog: keep (nothing) / discard (`pause at=idle_since`) / split (`pause at=idle_since` + resume now).
- Export: `GET /export?format=json|csv` (CSV = one file per table, zipped).
- **Tests first:** retro weighting; idle actions map to the right API calls; export round-trip (row counts match).

### S11 Ship for others — S (Opus for signing/updater trouble)
- Onboarding (F15): keys → keyring (D17), categories, observation explainer. At least one provider key required.
- `/ponytail-debt` + `/ponytail-audit` → fix what matters before release.
- Release workflow on tag `v*`: tauri-action builds the installer, the Tauri updater signs it (an updater keypair in GitHub secrets — this is not Authenticode), then a GitHub Release with `latest.json`.
- **Code-signing decision (user):** unsigned (SmartScreen warning), or SignPath Foundation (free for OSS, needs approval), or Azure Trusted Signing (paid, needs identity verification).
- Optional landing page / README polish → `taste-skill`.
- **Evidence:** a fresh Windows user profile install walkthrough (screenshots), the release on GitHub, an update from v0.1.0 → v0.1.1 working.

After S11: SPEC.md update for Phase 2 (Brain Dump), not a new doc set.

---

## 3. Cross-cutting rules for every slice
- Tests: backend `uv run pytest` (CI: `-m "not live"`), UI `npm test` (Vitest), e2e Playwright from S3.
- A schema change = a new Alembic revision + a migration test from the previous head with data present.
- No new dependency without one line in the slice plan saying why the stdlib or an installed one isn't enough.
- Every `shortcut:` comment names its limit and the trigger to upgrade.
- If the SPEC is wrong or silent → fix SPEC + add a CHANGES.md entry in the same PR. Never work around it silently.

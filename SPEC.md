# Kab Tak — SPEC (living spec, single source of truth)

> Phase 1 of a 4-phase series (Kab Tak → Brain Dump → Nudge/Initiator → AI Body Double).
> Edit this file when the product changes and add an entry to `CHANGES.md`. Never create a parallel spec.

---

## 1. Product

### 1.1 Problem
Time blindness: I estimate 20 minutes, the task takes 50, and the day collapses. To-do apps trust my
estimates. This app assumes my estimates are wrong **in a consistent, measurable way** and learns the
correction from my own history.

### 1.2 Users
- **Primary:** me (Akshat), a CSE student on Windows, logging study work (DSA lectures, coding practice,
  theory subjects, assignments, project coding).
- **Later:** anyone who installs the app on Windows and brings their own free API key.

### 1.3 Core loop
1. **Tell it the task in chat**, in plain words, including my own time guess.
   > "Video 2, 30 min left on backtracking. Then handwrite both problem codes, then implement them on
   > laptop. I think 1.5 hours."
2. The app shows a **task card** it parsed from the message: title, category, parts with quantities,
   my estimate. I confirm or correct it in one click.
3. **"start"** starts the timer. **"break" / "back"** pause and resume. **"done"** stops it.
4. On stop, one tap: **Done / Partly / Stuck**. For *Partly* I can say what got finished
   ("only implemented one") and the parts' completed quantities are updated.
5. The app stores estimate vs actual, and (after the observation period) shows a calibrated prediction.

### 1.4 Two modes
| Mode | When | What the user sees |
|---|---|---|
| **Observation** | First 7 days after install (default), and any category with < 5 completed tasks | Estimate vs actual only. No predictions shown. Predictions are still computed and stored silently ("shadow mode") so accuracy can be evaluated later |
| **Prediction** | After 7 days, per category that has ≥ 5 completed tasks | After I type my guess, the app reveals: "Likely 2h 20m (2h–2h 50m)" plus my last 5 similar tasks |

Both thresholds live in settings. The UI shows per-category progress: "Learning DSA (3/5)".

### 1.5 Features (Phase 1 scope)
- **F1 Chat capture** — natural-language task creation and timer control.
- **F2 Task card** — parsed, editable, confirm before saving.
- **F3 Timer** — start / pause / resume / stop, wall time and active time, survives app restart.
- **F4 Outcome** — Done / Partly / Stuck, with completed-quantity updates for Partly.
- **F5 Overrun check-in** — when my estimate runs out: "Still on it?" (keep going / done / stuck). Timer keeps counting.
- **F6 Forgotten timer recovery** — on launch, if a timer was running: "Were you still working? Stop at ___".
- **F7 Retro log** — "I did CN unit 1 for about 40 min" → logged with `source=retro` and lower weight.
- **F8 Today view** — list of tasks with guess vs actual and ratio.
- **F9 Calibration** — category multipliers (Level A), content rates (Level B), blend + range (Level C).
- **F10 Guess-first reveal** — prediction is shown only *after* my own estimate is entered.
- **F11 Insights** — per-category bias, my raw-guess error trend, interval coverage, model vs gut.
- **F12 Plan check** — paste a list of tasks with guesses → realistic total, chance it fits in available hours, what to drop.
- **F13 Mini timer** — small always-on-top window with time used vs my guess.
- **F14 Export** — all data as JSON and CSV.
- **F15 Onboarding** — first-run setup for other users: API keys, category list, observation explanation.
- **F16 Idle detection** — after N minutes of no keyboard/mouse input with a timer running: keep / discard / split.

### 1.6 Product rules (non-negotiable)
1. **Guess first, then reveal.** Never show a prediction before the user's own estimate is captured.
2. **The LLM never predicts duration.** It only converts chat into structured data. All numbers come from the user's own history.
3. **Every shown or shadow prediction is stored at the moment it is made**, with model version, so evaluation is honest.
4. **Logging must take seconds.** Simple commands ("start", "break", "back", "done") are handled without an LLM call.
5. **Tentative items** ("maybe I'll start video 3") are stored as tentative and never count toward a plan until started.
6. Tone is neutral and kind. No streaks, no shame language.

---

## 2. Architecture

### 2.1 Overview
```
┌──────────────────────── Tauri 2 app (Windows) ────────────────────────┐
│  React + Vite + TS UI  (chat, task card, today, insights, settings)   │
│  Rust shell: tray, mini-timer window, notifications, idle detection,  │
│              spawns + supervises the Python sidecar                   │
└───────────────┬───────────────────────────────────────────────────────┘
                │ HTTP on 127.0.0.1:<random free port>, per-launch token
┌───────────────▼──────────────── Python sidecar (FastAPI) ─────────────┐
│  api/        routes                                                   │
│  chat/       fast-path command parser + LLM parser                    │
│  llm/        provider chain: Groq → Cerebras → Gemini                 │
│  timer/      session state machine                                    │
│  calib/      Level A / B / C models, backtest, metrics                │
│  plan/       Monte Carlo plan check                                   │
│  db/         SQLModel + Alembic, SQLite file in %APPDATA%             │
└───────────────────────────────────────────────────────────────────────┘
```
- During development the UI runs in the browser (`vite dev`) against `uvicorn` directly.
- Before every Alembic upgrade at startup, `data.db` is copied to `data.db.bak-<current-revision>`; a failed migration stops the app.
- In release, the backend is bundled with PyInstaller as a Tauri **sidecar** binary.
- The backend is the long-term "time data core". Later phases (Telegram bot, Rust daemon, agent/MCP)
  talk to the same API.

### 2.2 Stack
| Layer | Choice |
|---|---|
| Desktop | Tauri 2, Windows only |
| UI | React 18+, Vite, TypeScript, Tailwind, Recharts |
| Backend | Python 3.12+, uv, FastAPI, Pydantic v2, SQLModel, Alembic |
| DB | SQLite (WAL mode), Postgres-safe schema (UUID text keys, UTC ISO-8601 timestamps, no SQLite-only types) |
| LLM | OpenAI-compatible client; Groq → Cerebras → Gemini (AI Studio) fallback chain |
| Modelling | numpy, scipy (NNLS), statsmodels; MAPIE later |
| Secrets | `.env` in dev; Windows Credential Manager via `keyring` in release |
| Tests | pytest, Hypothesis, Playwright; Vitest for UI units |
| Lint | ruff, mypy (backend); eslint, tsc (UI); cargo clippy (Rust) |
| CI | GitHub Actions on `windows-latest` |

### 2.3 LLM provider chain
- Order: **Groq (primary) → Cerebras → Gemini**. Move to the next provider on 429, 5xx, timeout (8 s), or
  invalid JSON after one repair retry.
- All providers are called through the OpenAI-compatible chat-completions format; base URL, model id and
  key come from config.
- Default model ids are in `config/llm.toml` and **must be verified against each provider's current docs
  when implementing** (model lists change).
- Request JSON output; validate with Pydantic. On validation failure: one retry that includes the
  validation error, then fall through to the next provider.
- Every call is logged to `llm_calls` (provider, model, latency, ok/error, token counts). No silent failures.
- If all providers fail: show "Couldn't understand that — fill the card manually" with an empty editable card.

### 2.4 Chat pipeline
1. **Fast path (no LLM):** regex/keyword match for `start`, `break|pause`, `back|resume`, `done|stop`,
   `stuck`, `partly`, `undo`, `today`. Case-insensitive, Hinglish-tolerant variants allowed.
2. **LLM path:** everything else goes to the parser with the system prompt in `chat/prompts/parse_task.md`,
   the list of categories and part types, and up to 10 recent correction examples (few-shot from the user's own fixes).
3. Output is an **intent**: `create_task | update_task | stop_with_outcome | retro_log | plan_check | question | unknown`.
S2 handles `create_task`, `question` and `unknown`; the other intents are recognised and answered "not available yet".
4. Anything that creates or changes data is shown as a card and needs confirmation (except fast-path timer commands).

### 2.5 Timer state machine
`draft → ready → running ⇄ paused → stopped`. Stop is legal from `running` or `paused`. Only one task can be `running` at a time; starting a second one
asks to pause or stop the first. Each running stretch is a `session` row. Active time = Σ sessions; wall time =
stop − first start.

---

## 3. Data & API contract

### 3.1 Tables (SQLModel)
| Table | Key columns |
|---|---|
| `categories` | id, name (unique), parent_id (nullable, for subcategories), created_at |
| `part_types` | id, key (e.g. `video_watch`), unit (`content_min`, `problems`, `units`, `pages`, `items`), label |
| `tasks` | id, title, raw_text, category_id, estimate_min, status, outcome (`done/partly/stuck/null`), tentative (bool), familiarity (`new/familiar/null`), source (`chat/retro/manual`), created_at, started_at, stopped_at, active_min, wall_min (both float minutes) |
| `task_parts` | id, task_id, part_type_id, planned_qty, completed_qty, order |
| `sessions` | id, task_id, start_at, end_at (nullable while running), end_reason (`pause/stop/idle/recovered`) |
| `predictions` | id, task_id, model_level (`A/B/C`), model_version, point_min, low_min, high_min, shown (bool), created_at |
| `corrections` | id, raw_text, llm_output_json, corrected_json, created_at — used as few-shot examples |
| `llm_calls` | id, provider, model, latency_ms, ok, error, prompt_tokens, completion_tokens, created_at |
| `settings` | key, value_json. Keys so far: `day_starts_at` (`"04:00"`), `installed_at` (UTC ISO, written at first DB init) |
| `events` | id, task_id (nullable), type, payload_json, created_at — append-only audit log |

Seed part types: `video_watch (content_min)`, `read_theory (units|pages)`, `handwrite_code (problems)`,
`implement_code (problems)`, `practice_problem (problems)`, `notes (pages)`, `assignment (items)`,
`project_coding (items)`, `other (items)`.
Seed categories: `DSA`, `Theory subject`, `Assignment`, `Project coding`, `Admin`.

### 3.2 LLM parse schema (Pydantic)
```json
{
  "intent": "create_task",
  "task": {
    "title": "Backtracking – Video 2 finish + 2 problems",
    "category": "DSA",
    "estimate_min": 90,
    "familiarity": "new",
    "tentative": false,
    "parts": [
      {"type": "video_watch",    "quantity": 30, "unit": "content_min"},
      {"type": "handwrite_code", "quantity": 2,  "unit": "problems"},
      {"type": "implement_code", "quantity": 2,  "unit": "problems"}
    ]
  },
  "extra_tasks": [],
  "confidence": 0.86,
  "clarifying_question": null
}
```
- `estimate_min` is null if the user gave no guess → the card asks for one (it is required to start).
- Multiple tasks in one message go into `extra_tasks`; tentative ones are flagged.
- `clarifying_question` is used only when a required field is missing.
- Code guard (ADR 0004): durations are parsed from the user's text (English, Hinglish, Devanagari). `estimate_min` is kept only if it equals one of them and that mention is not just a video's length; otherwise it is null. Titles lose durations the user did not write, and correction examples sent to the LLM show an estimate only under the same rule.

### 3.3 REST API (all JSON, prefix `/api`)
| Method & path | Purpose |
|---|---|
| `GET /health` | liveness + DB + version |
| `POST /chat` | `{text}` → `{intent, reply, cards[], parsed, parse_json}`; each card is a valid `POST /tasks` body |
| `POST /corrections` | `{raw_text, llm_output_json, corrected_json}`, sent when a card was edited before confirm |
| `POST /tasks` | create from confirmed card |
| `PATCH /tasks/{id}` | edit fields / parts |
| `POST /tasks/{id}/start` · `/pause` · `/resume` | timer control. `start`/`resume` return 409 `{detail, running_task_id}` when another task is running. `pause` takes optional `{at}` |
| `POST /tasks/{id}/stop` | `{outcome, completed_parts?, at?}` (legal from running or paused) |
| `GET /categories` · `GET /part-types` | seeded lookup lists (ids needed to create tasks) |
| `POST /tasks/retro` | retro log |
| `GET /tasks?date=YYYY-MM-DD` | today/any day view |
| `GET /tasks/running` | current running task (for recovery + mini timer) |
| `POST /predict` | `{draft task}` → prediction (stored; `shown` depends on mode) |
| `GET /calibration` | per-category multipliers, rates, sample counts, mode status |
| `GET /insights?range=7d|30d|all` | metrics for the insights screen |
| `POST /plan/check` | `{tasks[], available_min}` → realistic total, P(fit), drop suggestions |
| `GET /export?format=json|csv` | full export |
| `GET/PUT /settings` | thresholds, API keys status (never return keys), categories |

Auth: the Tauri shell passes a random per-launch token; the backend rejects requests without it and binds to 127.0.0.1 only. The token travels in the `X-KabTak-Token` header on every `/api/*` request. CORS allows only `http://localhost:5173` (dev) and `http://tauri.localhost` (release).

### 3.4 Calibration model
Notation: `E` = user estimate (min), `A` = actual active minutes, `r = ln(A / E)`.

**Training data rules**
- Use tasks with outcome `done`. Use `partly` only in Level B and only if completed quantities are known.
- Exclude `stuck` from fitting (actual time is a lower bound — censored). Keep them for later survival modelling.
- `source=retro` gets weight 0.5. Recency weight `w = 0.5 ** (age_days / half_life)`, `half_life = 21` (setting).
- Clip `r` to [ln(0.2), ln(5)] before fitting to limit outliers.

**Level A — category multiplier (empirical-Bayes shrinkage)**
- Global bias `b_g` = weighted mean of `r` across all categories (prior `ln(1.5)` when there is no data).
- Category bias `b_c = (Σw·r_c + k·b_g) / (Σw + k)`, `k = 3` (setting).
- Point prediction `P_A = E · exp(b_c)`.
- Interval: weighted 10th/90th percentiles of residuals `r − b_c` (category residuals pooled with global
  residuals when the category has < 15 samples) → `[E·exp(b_c+q10), E·exp(b_c+q90)]`.

**Level B — content rates (activates when tasks-with-parts ≥ 3 × number of active part types in a category)**
- Model: `A ≈ c₀ + Σ_k rate_k · qty_k`, solved with weighted non-negative least squares (scipy `nnls`
  on √w-scaled rows). `c₀` = per-task setup overhead.
- Uses `completed_qty` when present, otherwise `planned_qty` for `done` tasks.
- Output example: "1 content-min of lecture ≈ 1.8 min; handwrite 1 problem ≈ 15 min".

**Level C — blend + range**
- Blend in log space: `ln P = α·ln P_A + (1−α)·ln P_B`, with `α` set by inverse variance of each level's
  walk-forward log error over the last 30 eligible tasks.
- Range from the empirical quantiles of the blended model's walk-forward residuals.

**Evaluation (walk-forward, no leakage)**
- For each task in time order, predict using only tasks completed before it.
- Metrics: median |r| of the user's raw guess (gut error), median |ln(A/P)| of the model, bias (median r),
  80%-interval coverage, model-vs-gut improvement %.
- `predictions` table is the record of what was actually predicted at the time; backtests recompute separately.

**Plan check (Monte Carlo)**
- For each task: sample 2,000 values of `P · exp(ε)` with ε drawn from that category's residuals.
- Add a transition buffer per task switch (setting, default 5 min).
- Output: median and 80th-percentile total, `P(total ≤ available)`, and a drop suggestion ranked by
  (low priority, widest interval).

---

## 4. Non-goals (Phase 1)
- No calendar sync, no scheduling into time slots (Phase 2).
- No Telegram bot, no voice input (Phase 2).
- No app blocking, drift detection or nudges beyond the overrun check-in (Phase 3).
- No conversational companion (Phase 4).
- No accounts, cloud sync, or server database.
- No macOS/Linux/mobile builds.
- No local LLM (Ollama etc.).
- No gamification, streaks or leaderboards.
- The LLM never estimates durations.

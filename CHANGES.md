# CHANGES (spec change log)

One entry per change to SPEC.md: what changed and why. Newest first.

## 2026-11-22 — S0 doc fixes
- ADR 0001: data path is `%APPDATA%\KabTak\data.db` (was the old project name); added the `KABTAK_DB_URL` override (D1).
- SPEC §3.3: auth header is `X-KabTak-Token`; CORS origins listed (D12).
- Removed MASTER_PROMPT.md (its job is done).

## 2026-11-22 — Initial spec
- Created SPEC.md, ROADMAP.md, ADRs 0001–0005 from the discovery chat.
- Key choices: chat-first capture, 7-day observation mode with shadow predictions, SQLite, Groq → Cerebras → Gemini, Tauri + Python sidecar, Sonnet-default build.

## 2026-11-22 — Renamed project
- "Time Calibrator" renamed to **Kab Tak** (repo: AkshatTm/Kab-Tak).

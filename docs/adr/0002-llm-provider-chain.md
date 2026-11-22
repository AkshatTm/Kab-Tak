# ADR 0002 — Cloud LLM provider chain: Groq → Cerebras → Gemini

**Status:** Accepted · 2026-11-22

## Context
The laptop has little free storage, so no local model. Chat messages must be converted into structured
task data. Free tiers exist but each has rate limits and changing model lists. Privacy is not a concern for this user.

## Decision
- One OpenAI-compatible client with a fixed fallback order:
  1. **Groq** (groq.com — the inference provider, not xAI's Grok) — primary
  2. **Cerebras** — first fallback
  3. **Google Gemini via AI Studio** — second fallback (Gemini's OpenAI-compatible endpoint)
- Fall through on 429, 5xx, timeout (8 s), or JSON that fails Pydantic validation after one repair retry.
- Base URLs, model ids and timeouts live in `config/llm.toml`. Model ids are verified against provider docs at implementation time.
- Keys: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY` — `.env` in dev, Windows Credential Manager (`keyring`) in release. Never committed, never returned by the API, never bundled in the installer.
- Simple timer commands use a fast path with no LLM call.

## Consequences
- Works on free tiers at this app's volume (tens of short calls a day).
- For other users: they add their own free key(s) in onboarding. At least one provider key is required.
- Every call is logged in `llm_calls` for debugging and provider-health stats.

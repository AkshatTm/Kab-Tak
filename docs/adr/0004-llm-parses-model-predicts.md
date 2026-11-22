# ADR 0004 — The LLM parses; only the statistical model predicts

**Status:** Accepted · 2026-11-22

## Context
An LLM could be asked "how long will this take?", but it knows nothing about this user's history, and
its answers are not measurable or reproducible.

## Decision
- The LLM's only jobs: intent detection and extraction of task, category, parts, quantities, estimate, tentative flag.
- All durations shown to the user come from the calibration model (SPEC §3.4) trained on that user's own logs.
- Prompts must explicitly forbid the LLM from inventing or suggesting durations; any `estimate_min` it
  returns must come from the user's own words. Tests check this with sentences that contain no estimate.

## Consequences
- Predictions are explainable ("DSA multiplier 1.6 from 12 tasks") and testable.
- The ML part is a real, defensible model — the core of the project.

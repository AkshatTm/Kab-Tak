# ADR 0005 — Observation mode with shadow predictions

**Status:** Accepted · 2026-11-22

## Context
For the first days there is too little data for useful predictions, and showing predictions early would
anchor the user's own guesses.

## Decision
- **Observation mode** for the first 7 days after install (setting) and for any category with < 5 completed tasks (setting).
- During observation, predictions are still computed for every task and stored with `shown = false`.
- Prediction mode turns on **per category** when both conditions are met.
- In prediction mode, the prediction is revealed only after the user's own estimate is captured.

## Consequences
- On day 8 there is already an honest accuracy record of what the model *would have* said.
- Users who log more get predictions sooner in busy categories.
- The UI must show learning progress per category.

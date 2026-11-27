# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: the author, a CSE student on Windows who logs study work (DSA lectures, coding practice,
theory subjects, assignments, project coding), often late at night, keyboard-heavy. Decisions are made
for this user first. Later audience: other students and self-learners who underestimate how long study
and coding tasks take, many with time blindness or ADHD traits; onboarding covers them.

## Product Purpose

Kab Tak ("how long?") fixes time blindness. The user types a task and their own time guess, the app
times the work, learns how far their guesses are off per category from their own history, and shows a
calibrated time only after they have guessed. Success: logging takes seconds, and guesses can be
compared with reality honestly.

## Positioning

It assumes the user's estimates are wrong in a consistent, measurable way and corrects them from that
user's own logs. The LLM only turns chat into structured data and never predicts a duration.

## Operating Context

- Windows desktop app (a Tauri shell around a React UI and a local Python backend); in development the
  UI runs in the browser.
- The main loop: type the task in plain words (English, Hindi or Hinglish), check the parsed task card,
  confirm, start, pause, resume, stop, mark Done, Partly or Stuck.
- Observation period first: only guess against actual. Predictions appear per category after enough
  completed tasks.

## Capabilities and Constraints

- Screens (SPEC.md and DESIGN_BRIEF.md): chat, task card, mini timer, Today, Insights, plan check,
  settings and onboarding. Built slice by slice (ROADMAP.md).
- Data stays on the machine in SQLite. No accounts, cloud sync, calendar sync, app blocking or
  gamification.
- The chat parser calls free LLM providers with the user's own API key; if all fail, the user fills
  the card by hand.
- Terms: estimate (the user's guess), actual, ratio, task card, parts, category, outcome, observation
  mode, prediction mode.

## Brand Commitments

- Name: Kab Tak.
- Voice: calm, honest, a bit warm; a good lab notebook, not a game. Never shaming ("This took 2.1x
  your guess", not "You failed your estimate"). Short sentences. Numbers first, explanation second.
- Binding visual constraints from the brief: dark by default with a light mode; low-saturation
  neutrals with one accent for the running timer and primary actions; a calm, distinct colour for
  "over estimate", not alarm red; tabular figures for times and ratios; compact enough that chat and
  the current task fit a 1366x768 screen without scrolling.

## Evidence on Hand

No user history, testimonials or benchmarks yet. Do not invent task data, accuracy figures or
predictions for demos.

## Product Principles

1. Guess first, then reveal: no prediction before the user's own estimate.
2. Every number comes from the user's own history and can explain how it was computed.
3. Logging takes seconds.
4. Neutral and kind: no streaks, no shame language.
5. Numbers first, explanation second.

## Accessibility & Inclusion

WCAG AA contrast, everything keyboard reachable, no colour-only meaning, and layouts that stay usable
with enlarged text or Windows display scaling.

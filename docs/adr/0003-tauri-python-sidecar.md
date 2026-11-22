# ADR 0003 — Tauri 2 shell + Python FastAPI sidecar

**Status:** Accepted · 2026-11-22

## Context
Need a small, fast Windows desktop app with tray, notifications and an always-on-top mini window, while
keeping the ML/backend in Python. Later phases need a reusable local "time data core".

## Decision
- **Tauri 2** (Rust) for the shell: windows, tray, notifications, idle detection, sidecar lifecycle.
- **React + Vite + TypeScript** UI, developed in the browser first.
- **FastAPI** backend bundled with **PyInstaller** as a Tauri sidecar; listens on `127.0.0.1` on a free
  port chosen at launch; Tauri passes the port and a random per-launch auth token to the UI.
- The shell restarts the sidecar if it dies and shuts it down on exit.

## Consequences
- Small installer compared with Electron; Rust experience feeds Phase 3.
- Packaging the sidecar is the riskiest step → slice S4 is tagged Opus.
- The HTTP API doubles as the integration point for Phases 2–4 (bot, daemon, agent/MCP).

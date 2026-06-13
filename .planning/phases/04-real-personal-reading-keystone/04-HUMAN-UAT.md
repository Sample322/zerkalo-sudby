---
status: partial
phase: 04-real-personal-reading-keystone
source: [04-VERIFICATION.md]
started: 2026-06-13
updated: 2026-06-13
---

## Current Test

[awaiting human testing — requires a live stack: backend with a real ANTHROPIC_API_KEY + Postgres + Redis, frontend pointed at an HTTPS tunnel, opened in Telegram]

## Tests

### 1. Per-deck divergence (Core Value, READ-11)
expected: The same question submitted on 2–3 decks (e.g. Тени, Сердце/Любовь, Лесной) produces noticeably different tone AND focus, each with a recognizable per-deck signature (D-02). No result text contains «AI / нейросеть / модель / ИИ».
result: [pending]

### 2. Live-API smoke (READ-03/05/06)
expected: `cd backend && ANTHROPIC_API_KEY=<real> uv run pytest -q -m live` (or the live-marked smoke) returns a valid `ReadingOutput` across the 6 decks / 7 spreads with plausible Russian copy (D-14).
result: [pending]

### 3. Ritual covers latency + failure UX (D-07/D-08)
expected: A normal reading — the ~3s ritual covers the real LLM wait with NO spinner; reveal only after JSON is ready. A forced failure (bad key / induced timeout) shows «Колода замолчала…» + Повторить + Сменить колоду (question preserved), and the limit was NOT consumed (retry is free).
result: [pending]

### 4. Crisis tone (SAFE-03)
expected: A crisis-style question returns a warm, human, supportive response that fully breaks the mystical frame and points to a real person/specialist (generic wording, no phone number — D-04), with NO cards drawn and NO charge.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

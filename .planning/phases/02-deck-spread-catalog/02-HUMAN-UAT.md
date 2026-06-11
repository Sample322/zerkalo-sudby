---
status: partial
phase: 02-deck-spread-catalog
source: [02-VERIFICATION.md]
started: 2026-06-11T14:15:00Z
updated: 2026-06-11T14:15:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visible per-deck re-theming (UI-02 / criterion 2 core)
setup: backend up (`docker compose up` → `alembic upgrade head` → `python -m app.seed`), then `npm run dev`; open the authenticated Mini App.
steps: Select two different decks in the carousel.
expected: Background and accent visibly change between decks (one of the 6 palettes each), smooth ~400ms transition; `data-deck` flips on `<html>`.
result: [pending]

### 2. Live recommendation over HTTP + WR-01 reason accuracy (criterion 3)
setup: seeded backend up.
steps: Pick a topic with a compatible deck (e.g. «Любовь» + Сердечный Оракул), then a no-match combo (e.g. topic=День + Сердечный Оракул).
expected: A recommended spread + reason renders for both. For the no-match (topic-only/fallback) case, the reason must NOT falsely claim the spread is specially suited to the requested deck (WR-01).
result: [pending]

### 3. No-broken-image fallback in the live carousel (DECK-05 / criterion 4)
setup: seeded backend up, `npm run dev`.
steps: Browse the catalog and inspect deck preview tiles (and any rendered card-slot surfaces).
expected: Every art-less surface shows an atmospheric deck-tinted CSS/SVG placeholder — no broken-image icon, no failed art network request.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

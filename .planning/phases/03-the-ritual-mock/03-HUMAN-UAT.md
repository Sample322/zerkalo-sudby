---
status: partial
phase: 03-the-ritual-mock
source: [03-VERIFICATION.md]
started: 2026-06-12T15:15:00Z
updated: 2026-06-12T15:15:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Smooth flow end-to-end (UI-01/UI-03/D-01)
setup: `cd frontend && npm run dev`, open in the Telegram client (ngrok/cloudflared HTTPS), mid/low device.
steps: Walk onboarding → selection → ritual → reveal → result.
expected: Crossfades are continuous, no layout shift, no stutter or abrupt pop-in; load feels fast.
result: [pending]

### 2. Ritual prep ~3s + completion haptic + tap-to-skip (READ-07/D-08)
steps: Tap «Начать расклад»; watch the 3 beats + dimming + particles; feel the completion haptic; tap after the first beat.
expected: Three beats crossfade over ~3s, screen dims with a live particle field, a success haptic fires at completion, tapping after beat 1 skips early.
result: [pending]

### 3. Flip-reveal + «Раскрыть все» + per-flip haptic (READ-08/D-09)
steps: Reveal cards one-by-one, then tap «Раскрыть все»; feel the per-flip light haptic.
expected: Each card flips with a 3D turn + light haptic; «Раскрыть все» staggers the rest so it reads as a ritual, not an abrupt jump.
result: [pending]

### 4. Telegram light/dark theme + safe-area insets (UI-04)
steps: Open in the Telegram WebView on a notched device, toggle the app light/dark theme.
expected: Colors adapt to the Telegram theme; content respects safe-area top/bottom (SDK insets, not CSS env()).
result: [pending]

### 5. Per-deck theming carries through ritual→reveal→result (UI-02 carry / D-08)
steps: Pick different decks; check ritual/reveal/result backgrounds + accents.
expected: Per-deck palette carries visually through ritual → reveal → result.
result: [pending]

### 6. Sticky CTA not obscured by iOS keyboard (UI-01/HOME-07)
steps: Focus the question field on iOS.
expected: «Начать расклад» stays reachable above the keyboard.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

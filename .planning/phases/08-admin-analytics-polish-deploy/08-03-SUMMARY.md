---
phase: 08-admin-analytics-polish-deploy
plan: 03
title: Privacy-safe share-card (UI-06)
status: complete
completed: 2026-07-07
requirements: [UI-06]
---

# 08-03 — Privacy-safe share-card — SUMMARY

## What shipped
A client-only share-card that renders a completed reading to an image and shares it — the question
is EXCLUDED by construction.

- **`lib/shareCard.ts`** (framework-free): `renderShareCard(input)` paints an offscreen 1080×1350
  canvas (devicePixelRatio-scaled) — obsidian gradient + gold frame, the spread name (eyebrow), the
  deck name (title), up to 4 drawn cards (position + name + a ⟲ glyph when reversed), the closing
  line, and the «Зеркало Судьбы» mark — and exports a PNG `Blob`. `ShareCardInput` has **no
  `question` field**, so the personal question can never be drawn (UI-06 privacy). `shareOrDownload`
  uses the Web Share API when files are supported (`navigator.canShare({files})`) and falls back to a
  download; a user-cancelled share (`AbortError`) is swallowed. No new dependency, no backend route.
- **`ShareCardButton.tsx`** on the result (in `ReadingBody`, so it shows for BOTH the live result and
  a reopened past reading): an in-voice «Поделиться раскладом» button with saved / error hints.
- **Copy** (`reading/copy.ts`): `SHARE_BUTTON` / `SHARE_SAVED_HINT` / `SHARE_FAILED` — brand-safe.

## Verification
- **`tsc -b` clean; `vitest run` 128 passed** (+5 `shareCard.test`: the privacy invariant — input has
  no question key; Web-Share used when supported; download fallback; AbortError swallowed; render
  smoke returns a PNG blob with a mocked canvas). `copy.test.ts` banned-token scan green over the new
  SHARE_* constants (SAFE-06).

## Deviations / notes
- **Deck imagery not drawn:** `deck_cards.image_url` is empty in the seed (the app renders the CSS/SVG
  card-art fallback), so the card shows the drawn card NAMES + positions on a brand background rather
  than card art. Fully privacy-safe and self-contained; when real art is uploaded, `renderShareCard`
  can draw thumbnails later.
- **Server-side PNG + native Telegram prepared-message share deferred** (08-CONTEXT D-04) — the
  client-canvas + Web-Share/download path ships the value with zero backend surface; revisit only if
  the viral surface needs higher-fidelity output.
- No `card_shared` analytics event wired (it isn't in the 08-02 allowlist; the plan flagged it
  optional) — a one-line follow-on if share virality becomes a tracked metric.

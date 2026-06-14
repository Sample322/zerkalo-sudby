---
status: partial
phase: 05-history-profile
source: [05-VERIFICATION.md]
started: 2026-06-14
updated: 2026-06-14
---

## Current Test

[awaiting human testing — requires a live stack: backend with Postgres (+ a real reading or two created), frontend pointed at an HTTPS tunnel, opened in Telegram with a real session]

## Tests

### 1. History list + detail + swipe-delete/undo feel (HIST-02/03/04)
expected: Open Profile/History from the Home header icons. The history list shows past readings (date / question / deck / spread / card thumbnails / short summary), newest-first, with «Показать ещё» when there are more. Reopen a reading → it renders in the result view with a light fade-in (no re-ritual) and matches what was originally generated. Swipe a card to delete → it disappears with an undo snackbar (~5s); undo restores it. Empty state shows the §9.6 copy.
result: [pending]

### 2. Profile shows real Telegram identity (PROF-01)
expected: The Profile screen shows the real Telegram name + photo (from `GET /api/me`), the two toggles (reversals, history-personalization), and NO readings-count / subscription block (hidden until Phase 6/7). In-app back returns to Home.
result: [pending]

### 3. Settings persist server-side across reloads (PROF-02)
expected: Toggle reversals and/or history-personalization, fully reload the Mini App → the toggles reflect the persisted server value (not a local default). A new reading's reversals behaviour follows the persisted flag.
result: [pending]

### 4. Onboarding is server-primary, never re-shows (D-09)
expected: After completing (or skipping) onboarding once, reload / reopen the Mini App → onboarding does NOT re-appear (server `onboarding_completed=true` wins; localStorage is only a boot fallback). A returning user from before this phase is reconciled once.

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

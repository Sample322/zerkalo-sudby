# 03-03 Summary — Selection (question + «Начать расклад» → ritual)

**Plan:** 03-03 (Selection slice)
**Status:** complete
**Branch:** gsd/phase-03-the-ritual-mock
**Mode:** sequential (main tree); finalized by orchestrator after a transient executor auth blip (see Notes)

## What shipped
- **Task 1** (`710d646`): free-text **question input** added to `CatalogScreen` — 10–500 char validation via the store `questionValidity` helper with a gentle "уточни" hint when too short; **empty allowed → general reading** (HOME-01/02, D-13). Question rendered as a React text node (no `dangerouslySetInnerHTML`) — threat **T-3-01**. SpreadCard selection wired through the existing `selection` store.
- **Task 2** (`6892ed7`): the sticky **«Начать расклад»** CTA gated by `canStart({topic,deckSlug,spreadSlug})` (HOME-07). Handler runs the **required hand-off in order**: `await createReading({question,topic,deckSlug,spreadSlug,reversalsEnabled})` → `setReading(reading)` → `goTo("ritual")` (D-04/D-05, **W-2 store-slot writer contract** — the slot is populated before the step changes so 03-04/05/06 read it on first paint). The reading is never mirrored into component-local state.

## Requirements
HOME-01, HOME-02, HOME-03, HOME-04, HOME-05, HOME-06, HOME-07, UI-01, UI-04, SAFE-06 — covered. (Topic/deck/spread selection + recommendation reused from the Phase-2 `CatalogScreen`.)

## Verification
- `npm run test -- --run` → **64 passed** (11 files; incl. `CatalogScreen.test.tsx` 5 — asserts the store `reading` slot is the built `MockReading` before the step changes to "ritual").
- `npm run build` → green (tsc + vite, 512 modules).
- SAFE-06: reused the canonical `BANNED_BRAND_TOKENS` helper (no ad-hoc regex). `FlowRoot.tsx` NOT in the diff — only `CatalogScreen.tsx` + its test changed.

## Notes
- The executor agent completed both tasks' implementation + tests (64 green in the working tree) but hit a transient `403 Request not allowed` API error before committing Task 2 / writing this SUMMARY. Per the execute-phase safe-resume protocol, the orchestrator verified the work (contract present + ordered, full suite green, build clean), committed Task 2 (`6892ed7`), and wrote this SUMMARY. No code was re-generated.

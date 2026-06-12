# 03-06 Summary — Result screen

**Plan:** 03-06 (Result slice — closes the mock journey)
**Status:** complete
**Branch:** gsd/phase-03-the-ritual-mock
**Mode:** inline (orchestrator) — subagents on usage limit (see Notes)

## What shipped
- **Task 1 + 2** (`34a5ffe` screen, `75c5405` test): `frontend/src/components/result/ResultScreen.tsx` replaces the 03-01 stub (same export FlowRoot imports), rendering the full `MockReading` from the store `reading` slot (consume, never re-fetch):
  - Header «Расклад готов» (Display, accent).
  - **Meta row** (Label eyebrow + value): вопрос (rendered as a **React text node** — T-3-01; null → «Общий расклад» per D-13), тема, колода, расклад, дата (deterministic `DD.MM.YYYY` from the ISO date part — no timezone/locale drift).
  - **One glass card per drawn card** (deck-var glass recipe): `CardArt` thumbnail + position title + name (Heading, accent) + RU orientation label + short meaning + interpretation + the deck mystical accent in italic.
  - **Summary panel** — all five `reading.summary` fields (связка / главный фактор / внимание / совет / завершение) as a staggered "final gather" (`m.section` container `delayChildren: stagger(0.12)` + per-block opacity/y).
  - **Sticky action bar** padded by the Telegram SDK safe-area inset (`getSafeAreaInsets().bottom`, UI-04, never `env()`): «Ещё расклад» (accent primary, `whileTap`) wired to `startReadingAgain()` (D-04 — back to selection, question + topic preserved); «Сохранить карточку» + «История» present but **disabled** with a quiet «скоро» badge (D-12) — inert, no dead click.
  - Added `RESULT_GENERAL` to the canonical copy bank.

## Requirements
READ-09, UI-01, UI-03, SAFE-06 — covered.

## Verification
- `npm run test -- --run src/components/result/ResultScreen.test.tsx` → **4 passed**: all READ-09 fields render (header/question/topic/deck/spread/date + every card field + all 5 summary fields); «Ещё расклад» → step "selection" with question+topic preserved (D-04); save/история disabled + inert (D-12); whole rendered copy passes `containsBannedBrandToken` (SAFE-06).
- **Wave-merge gate:** full suite → **77 passed** (14 files); `npm run build` → green (tsc + vite, 512 modules).
- `FlowRoot.tsx` NOT in this plan's diff (stub swap is component-local).

## Notes
- Executed **inline by the orchestrator** (gsd-executor subagents hit the account usage limit, resets 5:30am MSK) — same TDD/commit discipline; `m.*` via the namespace import `import * as m from "motion/react-m"`; defensive no-reading guard returns an empty `<main>` (FlowRoot `() => Element` contract), FlowRoot untouched.

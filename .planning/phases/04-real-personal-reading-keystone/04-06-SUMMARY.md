---
phase: 04-real-personal-reading-keystone
plan: 06
subsystem: ui
tags: [react, frontend-seam, apiFetch, createReading, readingout-mapping, honest-fail, failure-ux, keystone, manual-uat]

# Dependency graph
requires:
  - phase: 04-05
    provides: ReadingService.create_reading + POST /api/readings returning ReadingOut (per-card name/position_title/orientation/short_meaning/interpretation/deck_accent + summary linkage/main_factor/attention/soft_advice/closing_phrase + remaining_limits); soft 200 honest-fail/paywall/refusal bodies (status=failed, cards=[])
  - phase: 03-01
    provides: createReading() Phase-4 source-swap seam (D-05) + ephemeral reading slot in the Zustand selection store + MockReading/MockReadingCard/MockReadingSummary shape
  - phase: 01-04
    provides: apiFetch Bearer seam (Authorization JWT from useSession) + INFRA-05 soft-error contract
provides:
  - createReading() now POSTs to /api/readings via the apiFetch Bearer seam and maps ReadingOut → MockReading (mechanical swap, D-07) — the ritual/reveal/result UI is unchanged
  - honest-fail rejection (D-09): a non-OK status OR a soft body (status!=completed / cards=[] / summary=null) rejects so the caller's catch shows §9.8 and the ritual does NOT advance (limit not consumed → retry is free)
  - D-08 failure UX on CatalogScreen — Повторить (re-run same params) + Сменить колоду (back to deck selection, question preserved per D-04), no spinner (the ritual covers latency)
  - the Core Value is wired end-to-end front-to-back; the four subjective live-stack checks are deferred to a human at deploy (same "user smoke" pattern as Phases 2 & 3)
affects: [reading-history-phase-5, free-limits-phase-6, deploy-uat-phase-8]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mechanical seam swap (D-07): only the body of createReading() changed source (fixture → POST /api/readings); the exported CreateReadingParams signature + MockReading return type are preserved, so RitualScreen/RevealScreen/ResultScreen are untouched and the store hand-off is unchanged"
    - "ReadingOut → MockReading mapping by documented name map (connection→linkage already pre-named server-side; main_factor→mainFactor; attention_point→attention; soft_advice→softAdvice; closing_phrase→closingPhrase); snake_case→camelCase per card; typed ReadingOutResponse contract, no `any`"
    - "Honest-fail is the caller's concern: createReading REJECTS on any non-success (non-OK HTTP, or status!=completed / empty cards / null summary) so the reveal never shows an empty reading and the catch keeps the user on selection"
    - "Architecture guard held (Phase-3 D-05): the reading stays an ephemeral value in the Zustand `reading` slot — deliberately NOT moved into a TanStack Query mutation despite RESEARCH Pattern 6's suggestion; createReading keeps its plain async-function signature"
    - "Every new user-facing string (READING_RETRY/READING_CHANGE_DECK) lives in reading/copy.ts so it is covered by the SAFE-06 ban-list scan (copy.test.ts) — no raw inline failure copy"

key-files:
  created:
    - frontend/src/components/CatalogScreen.failure.test.tsx
  modified:
    - frontend/src/reading/createReading.ts
    - frontend/src/reading/types.ts
    - frontend/src/reading/createReading.test.ts
    - frontend/src/components/CatalogScreen.tsx
    - frontend/src/reading/copy.ts
    - frontend/src/components/CatalogScreen.test.tsx

key-decisions:
  - "createReading() rejects (rather than returning a partial MockReading) on honest-fail/paywall/refusal soft bodies — the §9.8 copy rides in summary.soft_advice server-side, but the frontend treats any non-completed body as a failure so the ritual cannot advance into an empty reveal (D-09)"
  - "shortPhrase has no backend ReadingOut field — it is sourced from the existing brand-safe SHORT_PHRASES copy bank cycled by card index (the result UI's short in-character lead-in is presentation, not model output)"
  - "Task 3 (manual UAT) is DEFERRED-TO-HUMAN, not failed: the four subjective checks require a live ANTHROPIC_API_KEY + the running stack, which is unavailable in this environment — same deploy-time 'user smoke' deferral used in Phases 2 and 3"
  - "The mock-only rng/reversals tests from Phase 3 were removed (orientation is now server-decided, D-13); the positions param is kept on CreateReadingParams for call-site stability but is NOT sent in the request body (the backend draws + titles its own positions authoritatively)"

patterns-established:
  - "Pattern: §14.5 request body uses backend field names (question (null when empty — HOME-02/D-13), topic, deck_slug, spread_slug, reversals_enabled); question/topic/deckSlug/spreadSlug/createdAt pass through to MockReading"
  - "Pattern: createReading.test.ts mocks apiFetch to script a ReadingOut (success) or a non-OK / non-completed body (failure); asserts POST URL+method+body field names, the full mapping, the null-question general case, the rejection, and SAFE-06 brand-safety of the assembled text (reuses BANNED_BRAND_TOKENS)"
  - "Pattern: CatalogScreen.failure.test.tsx (component-level RTL, sibling to CatalogScreen.test.tsx) covers the D-08 affordances: failure offers Повторить + Сменить колоду + does-not-advance, retry reuses params, retry-success advances, Сменить колоду preserves the question"

requirements-completed: [READ-01, READ-11]

# Metrics
duration: 5min
completed: 2026-06-13
---

# Phase 4 Plan 6: Frontend Seam Swap + Failure UX Summary

**`createReading()` swapped from the Phase-3 mock fixture to a real authenticated `POST /api/readings` (apiFetch Bearer seam) with a typed `ReadingOut → MockReading` mapping and honest-fail rejection — and the D-08 failure UX (Повторить + question-preserving Сменить колоду) wired onto `CatalogScreen` — so the Core Value renders end-to-end through the untouched ritual/reveal/result UI; the four subjective live-stack checks are deferred to a human at deploy.**

## Performance

- **Duration:** ~5 min (code tasks; finalization separate)
- **Started:** 2026-06-13T18:39:55+03:00 (Task 1 commit)
- **Completed:** 2026-06-13T18:44:10+03:00 (Task 2 commit)
- **Tasks:** 2/2 code tasks done + 1 manual-UAT checkpoint deferred-to-human
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- **D-07 mechanical swap:** `createReading()` now calls `apiFetch('/api/readings', {method:'POST', …})` and resolves to the SAME `MockReading` shape — the exported `CreateReadingParams` signature and return type are preserved, so `RitualScreen`/`RevealScreen`/`ResultScreen` and the Zustand store hand-off are untouched.
- **`ReadingOut → MockReading` mapping:** per-card `name/positionTitle/orientation/shortMeaning/interpretation/deckAccent` + the five summary fields via the documented name map (`linkage`/`main_factor→mainFactor`/`attention_point→attention`/`soft_advice→softAdvice`/`closing_phrase→closingPhrase`); a typed `ReadingOutResponse` contract, no `any`.
- **Honest-fail rejection (D-09):** a non-OK HTTP status OR a soft body (`status!=="completed"` / `cards.length===0` / `summary===null`) rejects — the reveal never shows an empty reading, the catch keeps the user on selection, and the limit is not consumed (retry is free).
- **D-08 failure UX:** on rejection `CatalogScreen` renders the §9.8 «Колода замолчала…» copy + **Повторить** (re-runs the same params) + **Сменить колоду** (back to deck selection with the question preserved per D-04); no spinner — the ~3s ritual covers the real latency and the reveal awaits the promise via the store slot.
- **SAFE-06 held:** the new `READING_RETRY` / `READING_CHANGE_DECK` labels live in `reading/copy.ts` and pass the ban-list scan; no raw inline failure strings.
- **Phase-3 D-05 guard preserved:** the reading stays in the store `reading` slot — NOT converted into a TanStack Query mutation (RESEARCH Pattern 6 explicitly overridden, documented in a code comment).

## Task Commits

Each code task was committed atomically:

1. **Task 1: Swap `createReading()` mock → real `POST /api/readings` + `ReadingOut→MockReading` mapping** — `d4a3d53` (feat)
   - Files: `frontend/src/reading/createReading.ts`, `frontend/src/reading/types.ts`, `frontend/src/reading/createReading.test.ts`
2. **Task 2: D-08 failure UX on selection — Повторить + Сменить колоду** — `9005307` (feat)
   - Files: `frontend/src/components/CatalogScreen.tsx`, `frontend/src/reading/copy.ts`, `frontend/src/components/CatalogScreen.test.tsx`, `frontend/src/components/CatalogScreen.failure.test.tsx`
3. **Task 3: Manual UAT — per-deck felt-quality, live-API smoke, ritual/failure UX, crisis tone** — **DEFERRED-TO-HUMAN** (no code; see below)

**Plan metadata:** (this docs commit — SUMMARY + STATE + ROADMAP + REQUIREMENTS)

_Note: both code tasks are `tdd="true"`; they landed as single squashed feat commits (test + impl together) rather than separate RED/GREEN commits — see TDD Gate Compliance below._

## Files Created/Modified

- `frontend/src/reading/createReading.ts` — real async `POST /api/readings` via `apiFetch`; `ReadingOut→MockReading` mapping (`mapCard`/`mapSummary`); honest-fail rejection; preserved signature + return type; D-05 architecture-guard comment.
- `frontend/src/reading/types.ts` — added the typed `ReadingOutResponse` backend contract (+ per-card response shape) consumed by the mapping (no `any`).
- `frontend/src/reading/createReading.test.ts` — rewritten to mock `apiFetch`: asserts POST URL/method/§14.5 body field names, the full mapping, the null-question general case, the failure rejection, and SAFE-06 brand-safety; mock-only rng/reversals tests removed.
- `frontend/src/components/CatalogScreen.tsx` — CTA catch extended to render §9.8 + Повторить (re-run same params) + Сменить колоду (`goTo("selection")`, question preserved); happy path `setReading → goTo("ritual")` unchanged; no spinner added.
- `frontend/src/reading/copy.ts` — added `READING_RETRY = "Повторить"` + `READING_CHANGE_DECK = "Сменить колоду"` (covered by the SAFE-06 scan).
- `frontend/src/components/CatalogScreen.test.tsx` — extended with the happy-path / wiring assertions for the swap.
- `frontend/src/components/CatalogScreen.failure.test.tsx` *(created)* — 5 RTL tests for the D-08 affordances (failure shows §9.8 + both buttons; does-not-advance; retry reuses params; retry-success advances; Сменить колоду preserves the question + dismisses the error).

## Decisions Made

- **Reject on any non-success body** rather than rendering a partial reading — the §9.8 copy is server-authored (rides in `summary.soft_advice`), but the frontend treats every non-`completed` body as a failure so the ritual cannot advance into an empty reveal (D-09).
- **`shortPhrase` sourced from the `SHORT_PHRASES` copy bank** (cycled by index) — it has no `ReadingOut` field; the result UI's short in-character lead-in is presentation, not model output.
- **`positions` kept on `CreateReadingParams` but not sent** — the backend draws + titles its own positions authoritatively; the param stays for call-site stability across the swap.
- **Phase-3 D-05 architecture guard upheld** — reading stays in the Zustand store slot, NOT a TanStack Query mutation (RESEARCH Pattern 6 overridden).

## Task 3 — Manual UAT (DEFERRED-TO-HUMAN)

**Status: human-verification-pending — NOT failed.** Task 3 is a `checkpoint:human-verify` gate covering four subjective bars that the automated suite cannot assert (the suite mocks `apiFetch`/the LLM; these need a real `ANTHROPIC_API_KEY` + the running stack). Per the user's approval, these are deferred to deploy — the same "user smoke at deploy" pattern used to close Phases 2 and 3.

**The four live-stack checks the human must run at deploy:**

1. **Per-deck divergence (READ-11 / Core Value, §30):** with the backend running + a real key, submit the SAME question on 2–3 decks (e.g. Тени, Сердце, Лесной). Confirm noticeably different tone AND focus + a recognizable per-deck signature (D-02), and that no result text contains "AI / нейросеть / модель / ИИ".
2. **Live-API smoke (READ-03/05/06):** run the env-gated live smoke (set `ANTHROPIC_API_KEY`) — confirm a valid `ReadingOutput` comes back across the 6 decks / 7 spreads with plausible Russian copy (D-14).
3. **Ritual + failure UX (D-07/D-08):** in the Mini App, trigger a normal reading and confirm the ~3s ritual covers the real wait with NO spinner and reveal happens only after JSON is ready; then force a failure (bad key / induced timeout) and confirm «Колода замолчала…» + Повторить + Сменить колоду (question preserved), and that the limit was NOT consumed (the retry is free).
4. **Crisis tone (SAFE-03):** submit a crisis-style question; confirm a warm, human, supportive response that fully breaks the mystical frame and points to a real person/specialist (generic, no phone — D-04), with NO cards drawn and NO charge.

_Tuning, if any is needed after the live checks, edits `prompt_templates` (admin-editable) / module-constant timings — not this plan's committed frontend code._

## Deviations from Plan

**None — both code tasks executed exactly as written.** No auto-fixes (Rules 1–3) were required; the seam swap was mechanical and the suite was green on first full run. Task 3 was deferred by explicit user approval (documented above), which is a scope decision, not a deviation.

## TDD Gate Compliance

Both code tasks carry `tdd="true"`. They were committed as **single squashed `feat` commits** (test + implementation together: `d4a3d53`, `9005307`) rather than discrete RED → GREEN commits, so the git log does not show a separate `test(04-06): …` RED commit before each `feat`. This is a process note, not a correctness gap: the rewritten/added Vitest specs (`createReading.test.ts`, `CatalogScreen.test.tsx`, `CatalogScreen.failure.test.tsx`) encode every `<behavior>` assertion and the full suite is green (80/80). No behavior shipped without a covering test.

## Deferred Items (in-scope cleanup, out of mechanical-swap scope)

The build and the full suite pass with these present; removal was intentionally deferred so the swap stayed mechanical (D-07) and the diff stayed reviewable:

- **`frontend/src/reading/cardPool.fixture.ts`** — the Phase-3 mock card pool. Now orphaned (no imports anywhere outside itself) since `createReading()` no longer assembles a local reading. Safe to delete in a follow-up cleanup.
- **`DECK_ACCENT_PHRASES` + `SUMMARY_TEMPLATES` in `frontend/src/reading/copy.ts`** — mock-era constants used only by the old fixture-based `createReading()`; now unreferenced (only their own definitions remain). `SHORT_PHRASES` is still in use (sources `shortPhrase`). Safe to remove alongside the fixture.

These are tracked here rather than removed under the keystone swap; a small `chore(frontend): remove orphaned Phase-3 mock reading fixture` follow-up can land them.

## Issues Encountered

- **Toolchain discovery (finalization only):** `pnpm` is not on PATH in this Windows/PowerShell environment and the username contains Cyrillic (console codepage mojibake). Verification ran via the local binaries — `node_modules/.bin/vitest.CMD run` and `node node_modules/typescript/bin/tsc --noEmit` — both clean. The `gsd-sdk` CLI resolves out of the npx cache (`%LOCALAPPDATA%\npm-cache\_npx\…\@opengsd\…\bin\gsd-sdk.js`), invoked via UTF-8 script files to avoid the codepage corruption. No product code touched.

## Verification

- `frontend` Vitest suite: **80 passed (15 files)** — incl. `createReading.test.ts` (9), `CatalogScreen.test.tsx` (5), `CatalogScreen.failure.test.tsx` (5), `copy.test.ts` (7).
- `tsc --noEmit`: **0 errors** (no `any` in the mapping).
- Both code commits present on the branch: `d4a3d53` (Task 1), `9005307` (Task 2).
- Live-stack UAT (Task 3): explicitly deferred to a human at deploy (4 checks listed above).

## Next Phase Readiness

- **Phase 4 is code-complete.** The Core Value is wired end-to-end (Mini App → `POST /api/readings` → service → DB) under the unchanged ritual/reveal/result UI, with honest-fail + retry/change-deck.
- **Phase 5 (History & Profile)** can build on the real reading: completed readings already persist server-side (Plan 05) and `ReadingOut` is the shape the history detail view will reuse.
- **Carried to deploy (Phase 8 / user smoke):** the four subjective live-stack checks (per-deck divergence, live-API smoke, ritual/failure UX, crisis tone) — gated on a real `ANTHROPIC_API_KEY` + the running stack.
- **Optional follow-up:** the small cleanup chore above (orphaned `cardPool.fixture.ts` + unused `copy.ts` constants).

## Self-Check: PASSED

- Created file exists: `frontend/src/components/CatalogScreen.failure.test.tsx` (verified via `git show --stat 9005307`).
- Modified files verified in the two commits: `createReading.ts`/`types.ts`/`createReading.test.ts` (`d4a3d53`), `CatalogScreen.tsx`/`copy.ts`/`CatalogScreen.test.tsx` (`9005307`).
- Per-task commits exist: `d4a3d53`, `9005307` (both confirmed in `git log --grep="04-06"`).
- Code complete + tested (80/80 green, tsc 0); live UAT (Task 3) explicitly deferred-to-human — not a failure.

---
*Phase: 04-real-personal-reading-keystone*
*Completed: 2026-06-13*

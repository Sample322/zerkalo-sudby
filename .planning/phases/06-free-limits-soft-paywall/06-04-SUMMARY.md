---
phase: 06-free-limits-soft-paywall
plan: 04
subsystem: frontend
tags: [react, motion, paywall, throttle, bottom-sheet, toast, tanstack-query, brand-voice, d-08]

# Dependency graph
requires:
  - phase: 06-free-limits-soft-paywall
    plan: 02
    provides: "ReadingOut.reason='paywall' + reset_at (week_start+7d) on the HTTP-200 limit-block soft body — the FE paywall discriminant (D-04)"
  - phase: 06-free-limits-soft-paywall
    plan: 03
    provides: "HTTP 429 'throttled' on a >5/60s burst — the FE kind:'throttle' discriminant (D-08), distinct transport from the 200 paywall body"
  - phase: 05-history-profile
    provides: "ProfileScreen (the deliberately-omitted D-08 limits block) + its absence-asserting test; useMe()/usePatchSettings; GLASS language; UndoSnackbar transient setTimeout+AnimatePresence pattern"
  - phase: 04-real-personal-reading
    provides: "createReading seam (POST /api/readings → MockReading) + CatalogScreen.handleStart try/catch + the §9.8 READING_ERROR failure band"
provides:
  - "reading/createReading.ts: discriminated `ReadingError extends Error` with readonly `kind: 'throttle'|'paywall'|'failure'` + optional `resetAt` — ONE catch routes three surfaces (D-08); success path/signature/MockReading return UNCHANGED"
  - "reading/limitCopy.ts: pure `formatRemaining(left,total)` (clamp ≥0, NaN→'') + `formatReset(resetAt, now?)` (RU plural день/дня/дней ≤2d, genitive «D MMMM» beyond, «совсем скоро» fallback; UTC-based, timezone-independent)"
  - "components/PaywallSheet.tsx: persistent glass bottom-sheet + dimmed scrim, accent-tinted reset countdown, no purchase affordance / no alarm hue / no ticking clock (LIMIT-01, D-03/D-04)"
  - "components/ThrottleToast.tsx: transient glass pill (~3.75s auto-dismiss, UndoSnackbar pattern), THROTTLE_MESSAGE, distinct from the sheet (D-08)"
  - "CatalogScreen: freeLeft===0 CTA pre-check → sheet; catch kind-switch → throttle/paywall/failure; «Осталось N из 3» + 1-remaining accent hint; ProfileScreen un-hidden free-count block"
  - "copy.ts: PAYWALL_TITLE/PAYWALL_RESET_LEAD/PAYWALL_SOON_NOTE/PAYWALL_DISMISS/THROTTLE_MESSAGE/LIMIT_REMAINING_PREFIX/LIMIT_LAST_ONE_HINT/PROFILE_LIMIT_LABEL (verbatim UI-SPEC, ban-list clean)"
  - "api/auth.ts: SessionLimits += week_start? (backend LimitsOut already serializes it)"
affects: [07-payments (swaps PAYWALL_SOON_NOTE for real tariffs / a purchase affordance behind the same sheet)]

# Tech tracking
tech-stack:
  added: []  # zero new runtime dependency (UI-SPEC Registry Safety — hand-authored vs existing components + motion in the lockfile)
  patterns:
    - "Discriminated error transport: createReading throws a typed ReadingError{kind} so ONE catch in handleStart routes three visually/behaviorally distinct surfaces, never conflated (D-08) — the FE branches on err.kind / reason==='paywall', never on string-matching the copy"
    - "Transient-vs-persistent surface split: the throttle is a self-dismissing toast (setTimeout+AnimatePresence, the UndoSnackbar shape) and the paywall is a persistent sheet+scrim — motion + persistence encode the throttle/exhaustion distinction"
    - "Display-tier limit chrome: freeLeft (from useMe) + the freeLeft===0 CTA gate are non-authoritative; the server atomic-consume (06-02) + throttle (06-03) are the real gates — a user editing FE state can at most open/skip their OWN sheet (T-06-14 accept)"
    - "Pure interpolation helpers live in limitCopy.ts (imported by copy.ts's siblings) so the SAFE-06 ban-list scan reaches their leads; both NaN/invalid-guarded so the UI never flashes «NaN»/empty"
    - "Test-mock re-export: a vi.mock factory that stubs ONE export uses importActual + spread so a sibling export (ReadingError) the consumer uses via `instanceof` resolves to the real constructor under the mock"

key-files:
  created:
    - frontend/src/reading/limitCopy.ts
    - frontend/src/reading/limitCopy.test.ts
    - frontend/src/components/PaywallSheet.tsx
    - frontend/src/components/ThrottleToast.tsx
  modified:
    - frontend/src/reading/copy.ts
    - frontend/src/reading/types.ts
    - frontend/src/reading/createReading.ts
    - frontend/src/reading/createReading.test.ts
    - frontend/src/api/auth.ts
    - frontend/src/components/CatalogScreen.tsx
    - frontend/src/components/CatalogScreen.failure.test.tsx
    - frontend/src/components/profile/ProfileScreen.tsx
    - frontend/src/components/profile/ProfileScreen.test.tsx

key-decisions:
  - "ReadingError.kind values are exactly {throttle, paywall, failure}; resetAt is set ONLY on the paywall kind (carries data.reset_at). 429→throttle, non-OK other→failure, 200 non-completed reason==='paywall'→paywall, other 200 non-completed→failure."
  - "Inverted Profile test renamed to «D-09: the free-readings count block IS rendered (un-hides the Phase-5 D-08 block)» — asserts PROFILE_LIMIT_LABEL + formatRemaining(36,37)=«Осталось 36 из 37» PRESENT (was: not.toContain(37))."
  - "Count placement: a quiet Label ABOVE the «Начать расклад» CTA inside the sticky band (styled like START_GATE_HINT); at freeLeft===1 a second accent-tinted «Последний расклад на этой неделе» line (one tint bump, no size/weight bump); suppressed at 0 and while useMe pending; hidden during the failure band. Profile: a GLASS block between identity and settings, free count only."
  - "Pre-emptive paywall resetAt computed client-side as week_start+7d (computeResetAt, mirrors backend _compute_reset_at); the authoritative reset_at rides on the ReadingError on the belt-and-suspenders catch path."

patterns-established:
  - "Phase 7 swaps PAYWALL_SOON_NOTE for a real purchase affordance behind the SAME PaywallSheet (the sheet form + scrim + dismiss are reusable; only the note block becomes a CTA)."

requirements-completed: [LIMIT-01, LIMIT-03, LIMIT-05]

# Metrics
duration: 12min
completed: 2026-06-15
---

# Phase 6 Plan 04: Soft Paywall Sheet + Throttle Toast + Remaining-Count (FE) Summary

**The three locked UI-SPEC surfaces, all routed from ONE discriminated `createReading` error (D-08): a persistent soft paywall bottom-sheet with a per-user reset countdown (no fear, no «buy»), a transient throttle toast distinct from it, and a subtle «Осталось N из 3» count + 1-remaining accent hint on Catalog + the un-hidden Profile block — the Phase-5 absence test inverted to assert presence.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-15T20:28:30Z
- **Tasks:** 3 autonomous code tasks complete + committed; Task 4 is a `checkpoint:human-verify` (gate=blocking) — STOPPED here, awaiting a live-Mini-App approval (this plan is `autonomous: false`).
- **Files created/modified:** 13 (4 created, 9 modified)

## Accomplishments

- **Discriminated `ReadingError` transport (Task 1, D-08 — the seam that splits the three surfaces):** `createReading` now throws `class ReadingError extends Error` carrying a readonly `kind: "throttle" | "paywall" | "failure"` and an optional `resetAt`. The two former generic `throw new Error(...)` became: on `!response.ok` → `new ReadingError(status === 429 ? "throttle" : "failure", …)`; on a 200 non-completed body → if `data.reason === "paywall"` then `kind:"paywall"` carrying `data.reset_at` as `resetAt`, else `kind:"failure"`. The success path, the `createReading` signature, the `mapReadingOutToMock` transform, and the `MockReading` return type are **unchanged** (D-05/D-07 guard — only the error type is new). `ReadingOutResponse` gained `reason?` + `reset_at?`.
- **Pure limit helpers (Task 1, D-04/D-09):** `formatRemaining(left, total)` clamps `left` to ≥0 and returns `""` (render-nothing) on a NaN argument — never «Осталось -1 …»/«NaN из 3». `formatReset(resetAt, now?)` returns a brand-safe phrase: a sub-day/≤2-day reset → relative «через N дней» (RU plural день/дня/дней, rounded UP so a 6h reset is «через 1 день», never «через 0 дней»); beyond ~48h → an absolute genitive «20 июня»; a falsy/unparseable `reset_at` → «совсем скоро» (guards `new Date(null)`'s epoch-coercion footgun before construction). Day math is UTC-based, so it is timezone-independent.
- **PaywallSheet + ThrottleToast (Task 2, D-08):** `PaywallSheet` is a persistent glass bottom-sheet over a dimmed `--deck-bg ~70%` scrim, contents separated by 24px: `PAYWALL_TITLE` (display) / `PAYWALL_RESET_LEAD` + an accent-tinted `formatReset(resetAt)` span (the single hopeful focal point) / `PAYWALL_SOON_NOTE` (opacity-70) / a ≥44px dismiss glyph; scrim is tap-to-dismiss; motion `{opacity,y:24}↔{opacity,y:0}` `{0.28, ease[0.16,1,0.3,1]}`; safe-area bottom padding from the SDK insets (`Math.max(getSafeAreaInsets, getContentSafeAreaInsets)`), not viewport units; a soft `haptic.selection()` on open (never `notify`). `ThrottleToast` is a transient glass pill reusing the `UndoSnackbar` self-contained `setTimeout` (~3.75s) + `AnimatePresence` shape, `role="status" aria-live="polite"`, no buttons — visually and behaviorally distinct from the sheet. Both are purchase-free, alarm-hue-free, and `m.*` under LazyMotion.
- **Catalog wiring + Profile un-hide + inverted test (Task 3, D-09/D-10):** `CatalogScreen` computes `freeLeft = max(0, free_weekly_limit − free_used_this_week)` from `useMe` limits; a `freeLeft === 0` pre-check on the CTA opens the sheet **instead of** starting (resetAt = `week_start + 7d`); the `handleStart` catch routes `ReadingError.kind` → `throttle`→`ThrottleToast`, `paywall`→`PaywallSheet(err.resetAt)`, else→the existing `READING_ERROR` band. A quiet «Осталось N из 3» Label renders above the CTA when limits are present and `freeLeft > 0`; at `freeLeft === 1` a second accent «Последний расклад на этой неделе» line; suppressed at 0 and while `useMe` is pending. `ProfileScreen` un-hides the Phase-5 D-08 block as a `GLASS` count block (`PROFILE_LIMIT_LABEL` + `formatRemaining`) between identity and settings (free count only — no sub/paid/buy), and its omission comment now states D-09. The Phase-5 absence test was **inverted** (renamed + asserts presence).

## ReadingError.kind values (the D-08 discriminant — record for Phase 7)

| Backend signal | Branch in createReading | Thrown | resetAt | Surface |
|---|---|---|---|---|
| HTTP 429 (06-03 Redis burst) | `!response.ok && status===429` | `ReadingError("throttle", …)` | — | ThrottleToast (transient) |
| 200 body, `status!=="completed"` AND `reason==="paywall"` (06-02) | the non-completed branch | `ReadingError("paywall", …, data.reset_at)` | `data.reset_at` (= week_start+7d) | PaywallSheet (persistent) |
| any other non-OK status | `!response.ok && status!==429` | `ReadingError("failure", …)` | — | READING_ERROR band |
| 200 body, non-completed, NOT paywall (Phase-4 honest-fail) | the non-completed branch | `ReadingError("failure", …)` | — | READING_ERROR band |

## Inverted Profile test name (record)

`frontend/src/components/profile/ProfileScreen.test.tsx` — the Phase-5 `test("D-08: the readings-count / subscription block is NOT rendered …")` (was `expect(container.textContent).not.toContain(String(37))`) is now
`test("D-09: the free-readings count block IS rendered (un-hides the Phase-5 D-08 block)")` asserting `getByText(PROFILE_LIMIT_LABEL)` + `getByText(formatRemaining(36, 37))` («Осталось 36 из 37»; the mock is `free_weekly_limit:37, free_used_this_week:1`).

## Final count/hint placement (record)

- **Catalog (selection):** a Label line ABOVE «Начать расклад» inside the sticky bottom band, styled like `START_GATE_HINT` (`px-1 text-center text-sm opacity-70`). «Осталось N из 3» only when `limits && freeLeft>0`; at `freeLeft===1` a second `var(--deck-accent)` full-opacity line «Последний расклад на этой неделе»; nothing at `freeLeft===0` (the sheet carries it) or while `useMe` is pending/absent; hidden during the failure band.
- **Profile:** a `GLASS` block between the identity `<section>` and the settings `<section>` — `PROFILE_LIMIT_LABEL` «Бесплатные расклады» (eyebrow) + `formatRemaining(max(0, limit−used), limit)` (body). Free count only.

## Files Created/Modified

- **created** `frontend/src/reading/limitCopy.ts` — pure `formatRemaining` + `formatReset` (RU plural/genitive, NaN/falsy-guarded, UTC-based).
- **created** `frontend/src/reading/limitCopy.test.ts` — 12 tests (clamp, NaN-guard, plural 1/2, ISO accept, absolute genitive, «совсем скоро», sub-day round-up, ban-list).
- **created** `frontend/src/components/PaywallSheet.tsx` — persistent sheet + scrim (D-03/D-04).
- **created** `frontend/src/components/ThrottleToast.tsx` — transient pill (D-08).
- **modified** `frontend/src/reading/copy.ts` — PAYWALL_*/THROTTLE_*/LIMIT_*/PROFILE_LIMIT_LABEL constants.
- **modified** `frontend/src/reading/types.ts` — `ReadingOutResponse` += `reason?`/`reset_at?`.
- **modified** `frontend/src/reading/createReading.ts` — `ReadingError` class + the two discriminated throws; docstring updated.
- **modified** `frontend/src/reading/createReading.test.ts` — +4 tests asserting the three discriminated branches (429→throttle, paywall body→paywall+resetAt, non-OK other→failure, honest-fail→failure).
- **modified** `frontend/src/api/auth.ts` — `SessionLimits` += `week_start?`.
- **modified** `frontend/src/components/CatalogScreen.tsx` — pre-check + catch kind-switch + count line + 1-remaining hint + the two surfaces rendered.
- **modified** `frontend/src/components/CatalogScreen.failure.test.tsx` — mock factory re-exports the real `ReadingError` (deviation 1).
- **modified** `frontend/src/components/profile/ProfileScreen.tsx` — un-hidden free-count block + updated omission comment.
- **modified** `frontend/src/components/profile/ProfileScreen.test.tsx` — inverted the D-08 absence test → D-09 presence.

## Task Commits

Each task committed atomically (no hooks configured in the repo — plain commits):

1. **Task 1: discriminated ReadingError + limit copy + formatRemaining/formatReset** — `62d0f0c` (feat)
2. **Task 2: PaywallSheet + ThrottleToast** — `d07457e` (feat)
3. **Task 3: Catalog catch-routing + count + 1-remaining hint; un-hide Profile count; invert D-08 test** — `f0d4dfe` (feat)

**Plan metadata** (this SUMMARY + STATE/ROADMAP/REQUIREMENTS) committed separately.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `CatalogScreen.failure.test.tsx` mock omitted the new `ReadingError` export**
- **Found during:** Task 3 (full-suite run after wiring the catch).
- **Issue:** The pre-existing `vi.mock("../reading/createReading", () => ({ createReading: vi.fn() }))` factory did not export `ReadingError`. CatalogScreen now does `import { createReading, ReadingError }` and branches `err instanceof ReadingError`; under the mock `ReadingError` was `undefined`, so the `instanceof` check threw a `TypeError` inside the catch, the failure band never rendered, and all 5 failure-UX tests failed.
- **Fix:** Changed the factory to `async () => { const actual = await vi.importActual(...); return { ...actual, createReading: vi.fn() }; }` — it re-exports the REAL `ReadingError` class while still stubbing `createReading`. The default rejection (a plain `Error`) correctly falls to the catch's `else`→failure band. No production code changed.
- **Files modified:** `frontend/src/components/CatalogScreen.failure.test.tsx`
- **Commit:** `f0d4dfe`

### Verify-command false positives (rephrased comments, no behavior change)

**2. [Rule 3 - Blocking] Task-2 node guard tripped on comment prose (`env(` and «купи»/`Stars`/`buy`)**
- **Found during:** Task 2 verify.
- **Issue:** The guard does a literal-substring scan of the whole `PaywallSheet.tsx` source for `/env\(|100vh/` and `/купи|оплат|Stars|XTR|\bbuy\b/i`. My comments documenting the constraints ("never env()/100vh", "NO …/«купи»/«оплатить»", "no «buy»") contained those literal tokens even though the actual code/rendered copy contains none.
- **Fix:** Rephrased the comments to describe the same constraints without the literal banned tokens (e.g. "from the Telegram SDK insets, not CSS viewport units"; "NO payment/purchase affordance of any kind"; "no purchase control"). Same meaning; the guard then prints `OK components`. (Analogous to the 06-03 docstring/`get_session` false-positive.)
- **Files modified:** `frontend/src/components/PaywallSheet.tsx`
- **Commit:** `d07457e`

## Authentication Gates

None.

## Manual Verification Required (user-smokes — live deployed Mini App + live backend with an exhausted limit)

> This is Task 4 (`checkpoint:human-verify`, gate=blocking). The three surfaces are implemented and unit-tested headlessly (117 FE tests green), but their real rendering in the Telegram WebView (per-deck atmosphere, safe-area, motion, real exhausted-limit + 429 state) needs a live visual check. The plan is `autonomous: false` — the executor STOPS here and does NOT self-approve.

1. **Paywall (LIMIT-01, D-03/D-04):** with a deployed build + live backend, exhaust the 3 free readings for a test user; on the 4th, tapping «Начать расклад» surfaces the soft paywall bottom-sheet — confirm the headline «На этой неделе бесплатные расклады закончились», a sensible accent-tinted countdown («вернутся через N дней» / a date), the «скоро ещё» note, NO «buy»/price/Stars, NO red/alarm hue, and that dismissing preserves the question + selections.
2. **Count (D-09/D-10):** confirm «Осталось N из 3» shows quietly near the CTA at 2 and 3 left, shows the accent «Последний расклад на этой неделе» hint at exactly 1 left, is suppressed at 0 (the sheet carries it), and appears in the profile.
3. **Throttle (D-08):** fire reading requests rapidly (>5 within 60s) to trip the 429 — confirm the transient «Колода переводит дыхание…» toast appears, auto-dismisses (~3.75s), and is visibly DIFFERENT from the paywall sheet, then a normal-paced retry works.
4. **Brand (SAFE-06 / TZ §11.2):** scan all three surfaces for any «AI / ИИ / нейросеть / модель» or fear/pressure copy — there must be none.

## Test Results

- Full FE suite: **117 passed** (19 files), 0 failed — baseline 101 + 12 new `limitCopy` + 4 new `createReading` discriminated-branch assertions; the inverted ProfileScreen test + all CatalogScreen happy/failure tests green, not regressed.
- `node_modules/.bin/tsc --noEmit --pretty false` — **0 errors** (the `SessionLimits.week_start?` fix lands the `limits?.week_start` read).
- `node_modules/.bin/vitest run src/reading/copy.test.ts` — the new PAYWALL_*/THROTTLE_*/LIMIT_* constants pass the SAFE-06 ban-list (7 tests green).
- Task-2 node guard: `OK components` (no forbidden env/100vh, no purchase strings in the component sources).

## Next Plan Readiness

- **07-payments:** `PaywallSheet` is the reusable seam — Phase 7 swaps `PAYWALL_SOON_NOTE` for a real purchase affordance (Telegram Stars) behind the same sheet form + scrim + dismiss; the `ReadingError.kind` discriminant and the count surfaces are unchanged. The `Bucket` SUBSCRIPTION/PAID arms (06-02) feed the count once those balances are live.
- **Blocker (carried from 06-01/06-02):** migration 0002 must be applied against a live DB before the paywall/count can be live-verified end-to-end (the user-smokes above depend on a real exhausted-limit state).

## Self-Check

(verified below — created files present + all three task commits in history)

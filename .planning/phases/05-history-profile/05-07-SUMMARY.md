---
phase: 05-history-profile
plan: 07
subsystem: ui
tags: [react, tanstack-query, zustand, telegram, settings, onboarding, motion]

# Dependency graph
requires:
  - phase: 05-history-profile (05-03)
    provides: "PATCH /api/me/settings (SettingsPatch, JWT-scoped, partial update) + GET /api/me unchanged"
  - phase: 05-history-profile (05-04)
    provides: "backend reversals_enabled sourced from the persisted user flag (server enforcement)"
  - phase: 05-history-profile (05-05)
    provides: "FlowRoot SCREENS registry + PROFILE/SETTINGS copy strings + CatalogScreen header icons"
provides:
  - "me.ts client (fetchMe + patchSettings) over the existing apiFetch Bearer seam"
  - "useMe query (['me'], 60s staleTime) + usePatchSettings optimistic mutation (rollback + settle-invalidate)"
  - "ProfileScreen: Telegram identity (name + photo) + reversals/personalization toggles, NO readings-count/subscription block (D-08)"
  - "Onboarding flag migrated to SERVER-PRIMARY (D-09): FlowRoot gate reads GET /api/me, localStorage is boot fallback, completion PATCHes, one-time reconcile for legacy users"
  - "A new reading's reversals_enabled is sourced from the persisted GET /api/me flag, not the Phase-3 local toggle (D-09)"
affects: [phase-06, phase-07, payments, profile, settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-primary feature flag with localStorage boot fallback + one-time reconcile PATCH (no first-paint flash)"
    - "TanStack v5 optimistic settings mutation on a single stable key (['me']) — onMutate snapshot, onError rollback, onSettled invalidate"
    - "Persisted-setting source with local fallback until the query resolves (CTA never network-blocked)"

key-files:
  created:
    - frontend/src/api/me.ts
    - frontend/src/hooks/useMe.ts
    - frontend/src/components/profile/ProfileScreen.tsx
    - frontend/src/components/profile/ProfileScreen.test.tsx
  modified:
    - frontend/src/flow/FlowRoot.tsx
    - frontend/src/components/onboarding/OnboardingFlow.tsx
    - frontend/src/components/CatalogScreen.tsx
    - frontend/src/components/onboarding/OnboardingFlow.test.tsx
    - frontend/src/components/CatalogScreen.test.tsx

key-decisions:
  - "Onboarding flag is server-primary (GET /api/me settings.onboarding_completed); localStorage kept as boot fallback only; completion fires PATCH; legacy returning users (stale-false server flag + localStorage seen) get exactly one reconciling PATCH (D-09)"
  - "A new reading's reversals come from the persisted GET /api/me flag with the local Zustand toggle as fallback until useMe resolves; the local toggle stays in the store (harmless once the persisted flag is authoritative) (D-09)"
  - "Profile deliberately omits the readings-count/subscription block even though GET /api/me returns limits — the component test asserts the count is absent (D-08)"

patterns-established:
  - "Server-primary flag + localStorage boot fallback + one-time reconcile PATCH"
  - "usePatchSettings: optimistic ['me'] mutation (snapshot/rollback/settle-invalidate) mirroring the 05-06 delete recipe"

requirements-completed: [PROF-01, PROF-02]

# Metrics
duration: 60min
completed: 2026-06-15
---

# Phase 5 Plan 07: Profile/Settings + Onboarding Server-Migration Summary

**Profile/Settings screen (Telegram identity + reversals/personalization toggles, no count block) over an optimistic `usePatchSettings` mutation, plus the onboarding flag migrated to server-primary and a new reading's reversals now sourced from the persisted `GET /api/me` setting (D-08/D-09).**

## Performance

- **Duration:** ~60 min (across two sessions — Task 1 in a prior run, Task 2 here)
- **Started:** 2026-06-14 (Task 1)
- **Completed:** 2026-06-15T00:19:53+03:00 (Task 2 commit)
- **Tasks:** 2
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- **`me.ts` + `useMe`/`usePatchSettings`** (Task 1): `fetchMe`/`patchSettings` over `apiFetch`; `useMe` keyed `["me"]` (60s staleTime); `usePatchSettings` is the canonical TanStack v5 optimistic recipe (cancel → snapshot → optimistic merge into the cached `settings` → return snapshot; `onError` rollback; `onSettled` invalidate) targeting the single `["me"]` key.
- **ProfileScreen** (Task 1): renders the Telegram identity (name + photo, graceful fallback when absent), an in-app back affordance → Home (D-11), and the reversals + history-personalization toggles wired to `usePatchSettings` (optimistic, only the changed flag PATCHed). The readings-count/subscription block is deliberately NOT rendered (D-08), and the personalization explainer is brand-safe (SAFE-06, copy from `copy.ts`).
- **Onboarding server-migration** (Task 2): FlowRoot's initial-step gate is now SERVER-PRIMARY — `GET /api/me` `settings.onboarding_completed` is the truth, `hasSeenOnboarding()` is a boot fallback only (no first-paint flash), and a returning user whose server flag is stale-`false` but who has the localStorage flag set triggers exactly one reconciling `PATCH onboarding_completed: true` (guarded by `reconciledRef`). OnboardingFlow completion (both the final CTA and «Пропустить») fires `PATCH onboarding_completed: true` while keeping `markOnboardingSeen()` for the boot fallback.
- **Reversals source swap** (Task 2): `CatalogScreen` sources a new reading's `reversalsEnabled` from the persisted `GET /api/me` `settings.reversals_enabled` (via `useMe()`), falling back to the local Zustand toggle only until the profile query resolves so the CTA is never network-blocked (D-09). The backend already enforces this (05-04); the client now sends the persisted value for consistency.

## Task Commits

Each task was committed atomically:

1. **Task 1: me.ts client + useMe/usePatchSettings + Profile screen** - `ba9577a` (feat) — _committed in the prior session_
2. **Task 2: Onboarding server-migration (FlowRoot gate) + reversals-source swap (CatalogScreen)** - `9b7211f` (feat)

**Plan metadata:** _(this docs commit)_

## Files Created/Modified

- `frontend/src/api/me.ts` (created) — `fetchMe()` (GET /api/me) + `patchSettings(patch)` (PATCH /api/me/settings) over `apiFetch`; types reused from `api/auth.ts`.
- `frontend/src/hooks/useMe.ts` (created) — `useMe` query + `usePatchSettings` optimistic mutation on the single `["me"]` key.
- `frontend/src/components/profile/ProfileScreen.tsx` (created) — identity + two persisted toggles, no count block (D-08), back → Home (D-11), brand-safe copy.
- `frontend/src/components/profile/ProfileScreen.test.tsx` (created) — renders identity + toggles; toggle flips call `patchSettings` with only the changed flag; asserts the count value is absent (D-08).
- `frontend/src/flow/FlowRoot.tsx` (modified) — server-primary onboarding gate: boot-fallback effect (while `useMe` resolving) + server-primary effect (skip on complete; one-time reconcile PATCH for legacy users). `SCREENS` registry untouched (05-05 owns it).
- `frontend/src/components/onboarding/OnboardingFlow.tsx` (modified) — `finishOnboarding()` also fires `usePatchSettings().mutate({ onboarding_completed: true })`; `markOnboardingSeen()` retained as boot fallback.
- `frontend/src/components/CatalogScreen.tsx` (modified) — `reversalsEnabled` derived from `useMe().data?.settings.reversals_enabled ?? localReversals`; header-icon nav region (05-05) untouched.
- `frontend/src/components/onboarding/OnboardingFlow.test.tsx` (modified) — render now wraps a fresh `QueryClientProvider` (for `usePatchSettings`); new test asserts completion fires `PATCH { onboarding_completed: true }`.
- `frontend/src/components/CatalogScreen.test.tsx` (modified) — added a `GET /api/me` mock (reversals_enabled: true); new test proves the POST body's `reversals_enabled` is the persisted flag, not the local `false`.

## Decisions Made

None beyond the plan — the locked decisions D-08/D-09/D-11/SAFE-06 were implemented as specified. The FlowRoot gate written in the prior session (uncommitted in the working tree at resume) was verified against the plan's Task 2(a) requirements (server-primary decision, localStorage boot fallback, `reconciledRef`-guarded one-time reconcile, direct `setState` with no phantom back-history) and kept verbatim.

## Deviations from Plan

None - plan executed exactly as written.

The plan's Task 2 acceptance criteria explicitly allowed adding/adjusting tests to cover the server-primary path ("add/adjust a test only if needed"); the two new tests (onboarding-completion PATCH, persisted-reversals-source) cover exactly those paths. The OnboardingFlow test render was wrapped in a `QueryClientProvider` because `usePatchSettings` (now called by the component) uses `useQueryClient` — a required test-harness adjustment, not a behavior change.

## Issues Encountered

None. Baseline was 99 passing tests at resume (including the committed `ProfileScreen.test.tsx`). After Task 2: 101 passing (+2 new), `tsc --noEmit` 0 errors, `vite build` OK (520 modules).

## Known Stubs

None. Both Task-2 changes wire real persisted server data (`GET /api/me`) and a real mutation (`PATCH /api/me/settings`) — no placeholder values, hardcoded empties, or TODO markers introduced. (The local Zustand `reversalsEnabled` toggle is intentionally retained as a transient pre-resolve fallback, not a stub — the persisted flag is authoritative once `useMe` resolves and the backend enforces it regardless, 05-04.)

## User Setup Required

None - no external service configuration required. Note (HUMAN-UAT): Profile showing the REAL Telegram name/photo + settings persisting across reloads can only be verified on a live stack + Telegram (real identity + live backend) — a deploy-time smoke like Phases 2-4. The automated component tests run headless.

## Next Phase Readiness

- Phase 5 (History & Profile) is COMPLETE — all 7 plans shipped. A real user can now browse history, reopen a past reading, delete/undo, open Profile from Home, see who they are, and flip reversals/personalization (persisted server-side); onboarding never re-shows once the server records it.
- The `limits` payload from `GET /api/me` is already fetched but deliberately unsurfaced (D-08) — Phase 6/7 can surface the readings-count/subscription block on top of the existing `useMe` query without new plumbing.
- The persisted `reversals_enabled` is now the authoritative source for new readings (client + server agree); the local Zustand toggle remains as a harmless transient fallback that a future cleanup could remove.
- Verifier note: `verifier` + `code_review` + `security_enforcement` are enabled in config; `/gsd-code-review 5` + `/gsd-secure-phase 5` remain to run (mirroring the Phase-4 deferral) before phase close.

---
*Phase: 05-history-profile*
*Completed: 2026-06-15*

## Self-Check: PASSED

- Files verified present: `me.ts`, `useMe.ts`, `ProfileScreen.tsx`, `ProfileScreen.test.tsx`, `FlowRoot.tsx`, `OnboardingFlow.tsx`, `CatalogScreen.tsx`, `05-07-SUMMARY.md`.
- Commits verified in history: `ba9577a` (Task 1), `9b7211f` (Task 2).
- Gates: vitest 101 passed, `tsc --noEmit` 0 errors, `vite build` OK (520 modules).

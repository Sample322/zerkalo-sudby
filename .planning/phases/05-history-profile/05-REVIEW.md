---
phase: 05-history-profile
reviewed: 2026-07-05
depth: standard
files_reviewed: 10
files_reviewed_list:
  - frontend/src/components/history/HistoryScreen.tsx
  - frontend/src/components/history/UndoSnackbar.tsx
  - frontend/src/components/profile/ProfileScreen.tsx
  - frontend/src/components/result/ResultScreen.tsx
  - frontend/src/api/readings.ts
  - frontend/src/api/me.ts
  - frontend/src/hooks/useMe.ts
  - frontend/src/hooks/useReadings.ts
  - backend/app/api/users.py
  - backend/app/schemas/auth.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: resolved_partial
resolution:
  fixed: [WR-01]
  deferred: [IN-01, IN-02]
  resolved_date: 2026-07-05
---

# Phase 5: Code Review Report

**Reviewed:** 2026-07-05 · **Depth:** standard · **Files:** 10 · **Status:** resolved_partial

**Note:** authored inline by the orchestrator — the spawned `gsd-code-reviewer` hit a provider session
limit before writing output. Scope was narrowed to the Phase-5-distinctive surface: the history/profile
**frontend** (list, undo-delete, reopen, optimistic settings) + `users.py` + `schemas/auth.py`. The
backend `reading.py` reading-engine and `readings.py` list/detail/delete/restore endpoints were already
code-reviewed under Phase 4 (04-REVIEW.md) and were NOT re-reviewed here. Security was audited separately
(05-SECURITY.md, 20/20 incl. IDOR=HIGH) and not re-litigated.

## Summary

The history/profile surface is correct and battle-tested (live in production). The TanStack optimistic
recipes (delete → snapshot + rollback; restore → re-insert at original index + settle-invalidate) are the
canonical patterns and correctly keyed to the single `["readings","list"]` cache. One genuine (minor)
correctness issue in the UndoSnackbar timer, fixed; the rest are low-severity edge notes.

## Warnings

### WR-01: UndoSnackbar auto-dismiss timer resets on every parent re-render (FIXED)

**File:** `frontend/src/components/history/UndoSnackbar.tsx:32-36` + `HistoryScreen.tsx:76,136`
**Issue:** The 5s auto-dismiss `useEffect` depended on `[open, onDismiss]`, but `HistoryScreen` passes a
non-memoized inline `onDismiss` (`handleDismiss`) whose identity changes on every render. When the delete
mutation settles (or the list refetches) `HistoryScreen` re-renders → a new `onDismiss` → the effect
cleans up and re-arms → the 5s window is measured from the last render rather than from open, and a
continuously re-rendering parent would never auto-finalize. Impact was minor (the removal is already
committed optimistically + server-side; only the snackbar's dwell time drifts), but it is a real timer
coupling to unstable props.
**Fix (applied):** ref the latest `onDismiss` inside `UndoSnackbar` so the timer effect depends only on
`open` — armed exactly once per open, independent of parent memoization. History tests + tsc green.

## Info

### IN-01: a second delete while the undo window is open silently drops the first undo affordance

**File:** `frontend/src/components/history/HistoryScreen.tsx:65-68`
**Issue:** `handleDelete` overwrites `pending` for a single-snackbar model. Deleting reading B while A's
undo snackbar is open replaces A's pending with B's — A's undo affordance vanishes early. A is still
correctly soft-deleted server-side + removed from the cache, so there is no data inconsistency; only A's
undo window is cut short. Acceptable for MVP (rapid double-delete is an edge; the intended model is one
snackbar at a time). Fix if desired: queue pending deletes, or finalize A before opening B's snackbar.

### IN-02: `useDeleteReading` has no settle-invalidate; correctness relies on optimistic==server agreement

**File:** `frontend/src/hooks/useReadings.ts:66-89`
**Issue:** The delete mutation removes optimistically and rolls back on error but never invalidates
`["readings","list"]` on success — intentionally, to avoid a refetch flash, and safe because the server
soft-delete matches the optimistic removal. Documented as a deliberate tradeoff (T-05-STALE); noted only
so a future change that makes the server delete conditional would need to add the reconcile.

---

_Reviewed inline: 2026-07-05 · WR-01 fixed same-day._

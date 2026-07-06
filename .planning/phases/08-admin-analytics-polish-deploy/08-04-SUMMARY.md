---
phase: 08-admin-analytics-polish-deploy
plan: 04
title: In-character empty/error/loading polish (UI-05)
status: complete
completed: 2026-07-07
requirements: [UI-05]
---

# 08-04 — Empty/error/loading polish — SUMMARY

## Audit result (gap-audit, not a rewrite)
The sweep confirmed the app was already comprehensively in-voice — every per-query state renders a
`copy.ts` constant, with NO raw error text, HTTP statuses, stack traces, bare spinners, English
fallbacks, or TODO/FIXME markers found across the screens:

- History → `HISTORY_LOADING` / `HISTORY_ERROR` / `HISTORY_EMPTY`
- Profile → `HISTORY_LOADING` / `HISTORY_ERROR`
- Shop (tariffs) → `HISTORY_LOADING` / `HISTORY_ERROR`
- Result (detail load) → `HISTORY_LOADING`
- Catalog (deck/spread) → «Колода раскладывается…» / «Колода сейчас молчит. Загляни чуть позже.»
- Admin stats + the new Prompt-versions surface (08-01) → in-voice `Muted` states
- Share-card (08-03) → `SHARE_SAVED_HINT` / `SHARE_FAILED`

## The one real gap — fixed
There was **no app-level error boundary**: an unexpected render error would blank the screen (or show
a dev overlay) rather than product-voice copy — the one case the per-query states can't cover.

- **`components/ErrorBoundary.tsx`** — a class error boundary that catches any render error and shows
  an in-voice fallback («Отражение подёрнулось» + a soft hint + an «Обновить» reload button). The
  error details go to `console.error` for diagnostics ONLY; the user never sees a stack trace.
- Wrapped the whole authenticated surface in `App.tsx` (`ErrorBoundary` → `AuthGate` → `FlowRoot`).
- Copy: `APP_ERROR_TITLE` / `APP_ERROR_HINT` / `APP_ERROR_RETRY` (`reading/copy.ts`), brand-safe.

## Verification
- **`tsc -b` clean; `vitest run` 130 passed** (+2 `ErrorBoundary.test`: fallback shown when a child
  throws / children render through when healthy). `copy.test.ts` banned-token scan green over the new
  APP_ERROR_* constants (SAFE-06) — both light and every state stays in product voice.

---
phase: 7
slug: telegram-stars-payments
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-24
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Payments are
> security-critical: NO real charges in tests — use ЮKassa **test shop** creds + simulated
> webhooks + idempotency assertions. See `07-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.x + pytest-asyncio + httpx ASGITransport |
| **Framework (frontend)** | vitest |
| **Config file** | `backend/pyproject.toml` · `frontend/vitest` (in package) |
| **Quick run command** | `cd backend && uv run pytest -q` |
| **Full suite command** | `cd backend && uv run pytest -q` + `cd frontend && npx vitest run` |
| **Estimated runtime** | ~30s backend, ~5s frontend |

---

## Sampling Rate

- **After every task commit:** Run the quick backend suite (`uv run pytest -q`); for FE-only tasks, `npx vitest run`.
- **After every plan wave:** Run the full suite (backend + frontend) + `ruff check` + `tsc --noEmit`.
- **Before `/gsd-verify-work`:** Full suite green; ЮKassa flows tested against the **test shop** only.
- **Max feedback latency:** ~30s.

---

## Validation Principles (payments-specific)

- **No real money in any test.** Mock the `yookassa` SDK / re-GET call; never hit the live API in unit/integration tests. Live verification happens in HUMAN-UAT with ЮKassa **test mode** cards.
- **Idempotency is a tested invariant.** Deliver the same webhook event twice → access granted exactly once (assert balance/sub unchanged on the second delivery; assert the `UPDATE ... WHERE status=CREATED ... RETURNING` no-ops).
- **Grant only on re-fetched `succeeded`.** Tests assert no grant on payment-create, no grant on a forged/unconfirmed webhook body, grant only when the (mocked) re-GET returns `succeeded`.
- **Server-authoritative price.** Tests assert the charged amount is recomputed from the `products` row, never taken from the client.
- **Refund path** flips `Payment.status=refunded` + adjusts access; tested with a simulated `refund.succeeded`.

---

## Per-Task Verification Map

> Completed during planning / by the Nyquist auditor — each task maps to a requirement (PAY-01..08),
> a threat ref, the secure behavior, the test type, and an automated command.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD by planner_ | | | | | | | | | |

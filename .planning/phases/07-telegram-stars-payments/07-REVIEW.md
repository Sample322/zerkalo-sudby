---
phase: 07-telegram-stars-payments
reviewed: 2026-07-03T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - backend/app/services/payments.py
  - backend/app/api/payments.py
  - backend/app/services/reading.py
  - backend/app/services/telegram_auth.py
  - backend/app/api/users.py
  - backend/app/api/auth.py
  - backend/app/main.py
  - backend/app/core/scheduler.py
  - backend/app/core/config.py
  - backend/app/schemas/payment.py
  - backend/app/schemas/auth.py
  - backend/app/models/billing.py
  - backend/alembic/versions/0004_yookassa_payment_fields.py
  - backend/app/seed/loader.py
  - backend/app/seed/data/products.json
  - backend/pyproject.toml
  - frontend/src/api/payments.ts
  - frontend/src/api/auth.ts
  - frontend/src/hooks/usePayments.ts
  - frontend/src/components/shop/ShopTariffs.tsx
  - frontend/src/components/shop/ShopTariffs.test.tsx
  - frontend/src/components/PaywallSheet.tsx
  - frontend/src/components/profile/ProfileScreen.tsx
  - frontend/src/components/profile/ProfileScreen.test.tsx
  - frontend/src/lib/telegram.ts
  - frontend/src/reading/copy.ts
  - frontend/src/reading/limitCopy.ts
findings:
  critical: 2
  warning: 7
  info: 6
  total: 15
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-07-03
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Reviewed the ЮKassa direct-API money path (RUB packs + «Лунный доступ» recurring subscription) end-to-end: `PaymentService` core, the thin webhook/refund/cancel router, the recurring sweep, config/schemas/models/migration, and the shop FE (hooks + `ShopTariffs` + `PaywallSheet` + `ProfileScreen`). Per the review charter, the audited security mitigations (webhook re-fetch grant, IP-gate, idempotent atomic UPDATE, IDOR scope, server-price, refund-by-entitlement) were NOT re-litigated; the focus was correctness/logic, async/transaction handling, race conditions beyond the audited set, error-handling gaps, tz-aware/naive mixing, React hook correctness, dead code, and repo conventions.

The transaction and async plumbing is largely sound: the tenacity `AsyncRetrying` is correctly awaited (a plain `def` returning the coroutine that the `await`ing caller resolves), the multi-subscription sweep does NOT hit `MissingGreenlet` because production `SessionLocal` sets `expire_on_commit=False`, and the tz-aware `TIMESTAMP(timezone=True)` columns (`week_start`, subscription window) are consistently compared against `datetime.now(UTC)`.

However, there is one **headline correctness defect that breaks the paid model**: the subscription entitlement is claimed to be "window-gated" but is implemented as pure count-gating, and nothing resets the count bucket when the 30-day window naturally expires — so a lapsed/failed-renewal subscriber keeps unlimited readings forever (CR-01). A second Critical concerns the refund reconciliation ordering (money-moved / access-not-clawed-back window on a mid-operation crash, CR-02). The remaining findings are robustness and quality issues.

## Critical Issues

### CR-01: Subscription is count-gated, not window-gated — an expired subscription grants unlimited readings forever

**File:** `backend/app/services/reading.py:150-177` (`determine_access`) + `backend/app/services/payments.py:580-588` (`_grant_subscription`)

**Issue:**
The entire subscription design is documented as **window-gated**: the docstrings in both `payments.py` (lines 67-81, 471-472, 545-549, 708-716) and `reading.py` (`_consume_subscription_atomic`, lines 707-722) repeatedly assert *"determine_access selects the SUBSCRIPTION bucket only when the window is live"* and *"the real bound is `Subscription.current_period_end`"*. **The code does not implement this.**

- `determine_access(limits: UserLimits, ...)` receives ONLY the `UserLimits` row (line 150). `UserLimits` has no `current_period_end` / window field. It selects the SUBSCRIPTION bucket purely on the count invariant `subscription_spreads_limit - subscription_spreads_used > 0` (lines 170-174).
- The grant sets `subscription_spreads_limit = SUBSCRIPTION_WINDOW_UNLIMITED` (1_000_000_000) and `subscription_spreads_used = 0` (payments.py lines 585-587).
- The ONLY code path that ever resets `subscription_spreads_limit` back to `0` is a **refund** (`_revoke_subscription`, payments.py line 845). There is **no path that zeroes the bucket when the window expires naturally**:
  - a failed renewal charge sets `status = PAYMENT_FAILED` but keeps `current_period_end` and never touches `UserLimits` (payments.py lines 665-676);
  - a self-serve cancel keeps access to period end and never touches `UserLimits` (api/payments.py lines 224-226);
  - the sweep only re-charges ACTIVE, due subs — an EXPIRED/PAYMENT_FAILED/CANCELED sub is skipped, so nothing ever runs to zero the bucket after the window ends.

**Consequence:** Once a user buys any subscription, `subscription_spreads_limit` stays at 1e9 permanently. After their free quota is spent, `determine_access` returns `SUBSCRIPTION` and `_consume_subscription_atomic` always succeeds (1e9 is never reached), so the user gets **unlimited readings forever**, even months after the subscription lapsed / a renewal failed / they cancelled and the period ended. This directly defeats the paid model (the core deliverable of Phase 7) and is a revenue-loss bug, not a mere edge case.

Note this is NOT caught by the current tests: `test_payments_service.py` / `test_payments_scheduler.py` assert grant/renew/refund writes in isolation; no test drives `determine_access` (or `create_reading`) for a user whose subscription window has ended while the bucket is still 1e9.

**Fix:** The window must be an actual input to the access decision. Two workable approaches:

Option A (recommended — make the window authoritative at read time). Load the live subscription and pass its end into `determine_access`, selecting SUBSCRIPTION only when the window is live:
```python
def determine_access(
    limits: UserLimits, now: datetime | None = None, *, subscription_period_end: datetime | None = None
) -> Bucket:
    moment = now if now is not None else datetime.now(UTC)
    free_left = (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0)
    window_stale = limits.week_start is not None and limits.week_start <= moment - WINDOW
    if free_left > 0 or window_stale:
        return Bucket.FREE
    subscription_left = (limits.subscription_spreads_limit or 0) - (limits.subscription_spreads_used or 0)
    window_live = subscription_period_end is not None and subscription_period_end > moment
    if subscription_left > 0 and window_live:
        return Bucket.SUBSCRIPTION
    if (limits.paid_spreads_balance or 0) > 0:
        return Bucket.PAID
    return Bucket.NONE
```
and in `_consume_free_gate` fetch the active-window end (`_active_subscription`-style query) to pass in. Also add the same window predicate to `_consume_subscription_atomic`'s `WHERE` so the atomic gate cannot consume outside a live window.

Option B (expire the bucket lazily). On each auth/read, when the live subscription window has ended, run `UPDATE user_limits SET subscription_spreads_limit=0, subscription_spreads_used=0 WHERE user_id=…` (the same clean-up `_revoke_subscription` does). This keeps `determine_access` count-only but requires a reliable expiry trigger; a lazy check at read time is the correctness floor since the sweep is only proactive.

Either way, add a regression test: grant a subscription, set `current_period_end` in the past, spend the free quota, then assert `create_reading` returns the soft paywall (not an unlimited SUBSCRIPTION consume).

### CR-02: Refund calls ЮKassa BEFORE the local reconciliation — a crash in between refunds money without clawing back entitlement

**File:** `backend/app/services/payments.py:747-756` (`refund_payment`)

**Issue:**
`refund_payment` performs the external side effect first and reconciles second:
```python
await self._client.create_refund(payment_id=provider_id, value_rub=value, idempotence_key=f"refund:{provider_id}")
await self._reconcile_refund(session, payment)   # flip → REFUNDED + claw back entitlement
```
If the process crashes, the DB session errors, or the connection drops **after** `create_refund` succeeds but **before** `_reconcile_refund` commits, the money is refunded at ЮKassa while `paid_spreads_balance` / the subscription window are still fully granted. The user keeps the paid entitlement AND gets their money back. Unlike the webhook path (which is redriven by ЮKassa redelivery), the admin `refund_payment` entrypoint is a single request with no automatic retry, so this inconsistency is not self-healing.

The webhook `refund.succeeded` path DOES converge (it re-fetches and reconciles idempotently on redelivery), but the admin path is the "fully-deterministic reconciliation entrypoint" per its own docstring (lines 766-768) and must not depend on a webhook that may be filtered by the IP-gate or arrive late.

**Fix:** Make the reconciliation resilient to a post-refund crash. Preferred: record the refund intent locally and reconcile in a way the webhook can complete, OR reconcile immediately after the refund inside a try/except that logs a loud, actionable reconciliation-required error so ops can replay:
```python
await self._client.create_refund(payment_id=provider_id, value_rub=value, idempotence_key=f"refund:{provider_id}")
try:
    await self._reconcile_refund(session, payment)
except Exception:
    logger.exception(
        "refund_reconcile_failed_after_provider_refund",
        extra={"event": "payment.refund_reconcile_orphan", "payment_id": str(payment.id),
               "provider_payment_id": provider_id},
    )
    raise
```
Because `_reconcile_refund` is idempotent (its `WHERE status=PAID` flip no-ops on a second call) and the ЮKassa refund reuses the deterministic `refund:<provider_id>` key, the whole `refund_payment` is safe to re-invoke — but that safety is only realized if the failure is surfaced and retried rather than silently swallowed. Document/expose that replay path.

## Warnings

### WR-01: `find_due_subscriptions` selects due rows but the sweep never re-checks status → a concurrent cancel between select and charge still re-charges

**File:** `backend/app/services/payments.py:593-620` + `backend/app/core/scheduler.py:52-56`

**Issue:** The sweep loads the whole due set with one `find_due_subscriptions` query, then iterates charging each. Between the `SELECT` and the per-row `renew_subscription`, a user could `POST /subscriptions/{id}/cancel` (flipping `status=CANCELED`). `renew_subscription` does not re-assert `status == ACTIVE` before charging — it only looks up the product (lines 641-647) and charges. Result: a subscription cancelled seconds before the charge still gets billed for the next period. The deterministic idempotence key does not help (it is a *new* period key). With `expire_on_commit=False` the in-memory `sub.status` is also stale for the whole sweep, so even reading `sub.status` would not reflect the concurrent cancel.

**Fix:** Re-assert ACTIVE atomically as part of the renewal — either re-`SELECT ... WHERE id=… AND status=ACTIVE` (with `populate_existing`) at the top of `renew_subscription` and return early if not active, or gate the "advance period + write renewal row" on a conditional `UPDATE subscriptions SET period_index=… WHERE id=… AND status=ACTIVE RETURNING` so a cancelled row is skipped.

### WR-02: `_grant_subscription` "extends" the window by overwriting `current_period_start`/`current_period_end` with `now`-anchored values, discarding unused remaining time on an early re-buy

**File:** `backend/app/services/payments.py:551-574`

**Issue:** On a grant for an existing subscription row the code sets `current_period_start = now` and `current_period_end = now + days` (lines 571-574), unconditionally re-anchoring on the moment the webhook lands. For a normal end-of-period renewal this is fine, but if a subscriber re-purchases / a renewal lands early (e.g. sweep grace window fires a few days before expiry, or a user manually buys again mid-period), the remaining days of the current period are silently discarded rather than stacked. The docstring says "opens/extends" but the implementation always *replaces* from `now`.

**Fix:** Extend from the later of `now` and the existing `current_period_end`:
```python
base = now if sub is None or sub.current_period_end is None or sub.current_period_end < now else sub.current_period_end
sub.current_period_end = base + timedelta(days=days)
sub.current_period_start = now
```

### WR-03: Renewal `payment_method_id` fallback reads a column that never carries a payment-method id in production

**File:** `backend/app/services/payments.py:651-656` + `693` (`saved_method`)

**Issue:** `renew_subscription` computes `saved_method = subscription.payment_method_id or subscription.telegram_payment_charge_id`. `telegram_payment_charge_id` is the legacy Stars charge id (a *payment/charge* identifier), not a ЮKassa `payment_method_id`. Under ЮKassa it is always NULL for real rows (only the tests seed it as a "saved-method seam", per `test_payments_scheduler.py:74`/`test_payments_service.py:295`). Passing a Stars charge id as a ЮKassa `payment_method_id` would produce an invalid merchant-initiated charge. The fallback exists only to satisfy test fixtures and is dead/misleading in production; worse, if any legacy row ever had that column populated, it would be sent to ЮKassa as a payment method and fail. Same fallback pattern in `refund_payment` (line 747) is legitimate (both are payment ids), but the subscription one conflates two different id kinds.

**Fix:** Drop the `telegram_payment_charge_id` fallback in the renewal path and rely on `subscription.payment_method_id` only (guard `None` → treat as un-renewable → `PAYMENT_FAILED`). Update the two tests to seed `payment_method_id` instead of the legacy column.

### WR-04: Subscription buy shows "success" without any confirmation when the user already has an active subscription

**File:** `frontend/src/components/shop/ShopTariffs.tsx:91-99`

**Issue:** After returning from the ЮKassa page the subscription poll predicate is `Boolean(meData?.limits?.subscription_active)` (line 93). For a subscription re-buy / renew while a subscription is already active, `subscription_active` is already `true`, so the first immediate `pollMe` check returns `true` and the UI shows `SHOP_SUCCESS` even if the new payment never confirmed (or failed). Unlike the pack path, there is no "changed from previous state" delta — it is an absolute boolean.

**Fix:** Capture a pre-purchase discriminator and require a change, e.g. snapshot `prevPeriodEnd = me?.limits?.subscription_period_end` and treat success only when `subscription_active && subscription_period_end !== prevPeriodEnd` (the window moved), mirroring the `paid_spreads_balance > prevBalance` pattern used for packs.

### WR-05: Webhook body is schema-validated before the IP allowlist runs → a malformed body from ЮKassa returns 422 (retry storm) instead of a handled 200

**File:** `backend/app/api/payments.py:137-159` + `backend/app/schemas/payment.py:114-129`

**Issue:** `yookassa_webhook` declares `envelope: WebhookEnvelope` as a parameter, so FastAPI validates the body (requiring `type`, `event`, and a dict `object`) **before** the handler body runs — i.e. before `_client_ip` / `is_from_yookassa`. Consequences: (1) a ЮKassa event shape the model does not expect (missing/renamed field) returns 422, which ЮKassa treats as a failure and **keeps redelivering** (the docstring's own goal is "ALWAYS 200 on handled/duplicate so ЮKassa stops redelivering"); (2) the IP-gate no longer runs first for a malformed body, so the "cheap reject before any work" property is lost for that class of request.

**Fix:** Accept the raw request and gate on IP first, then parse defensively:
```python
async def yookassa_webhook(request: Request, session=..., service=...) -> Response:
    if not is_from_yookassa(_client_ip(request)):
        return Response(status_code=403)
    try:
        envelope = WebhookEnvelope.model_validate(await request.json())
    except Exception:
        return Response(status_code=200)  # unparseable → ack so ЮKassa stops; nothing to grant
    ...
```

### WR-06: `_ensure_user_limits` seeds a hard-coded free weekly limit that silently diverges from the model/config default

**File:** `backend/app/services/telegram_auth.py:44-45,166-169`

**Issue:** `_FREE_WEEKLY_LIMIT = 3` is a private constant in `telegram_auth.py`, duplicated against `UserLimits.free_weekly_limit` (`default=3, server_default="3"` in `billing.py:61-63`). Two sources of truth for the same business number (magic number, per repo `coding-style.md` "no hardcoded values"). If the product limit changes, one can be updated without the other, and rows created via the ORM default vs this INSERT would diverge.

**Fix:** Reference a single source — either omit `free_weekly_limit` from the INSERT and let the server_default apply, or import the limit from config/model rather than re-declaring it.

### WR-07: `usePollMeUntilGranted` writes the `["me"]` cache with a `MeResponse` cast to `AuthResponse` (missing `access_token`)

**File:** `frontend/src/hooks/usePayments.ts:68-69` + `frontend/src/api/me.ts:29-33`

**Issue:** `fetchMe()` calls `GET /api/me`, which returns `{user, limits, settings, is_admin}` with **no `access_token`** (the backend `MeResponse` omits it), yet is typed as `Promise<AuthResponse>` (`access_token: string` required) and then written into the shared `["me"]` cache via `qc.setQueryData<AuthResponse>(ME_KEY, me)`. Any reader that trusts `me.access_token` after a poll will read `undefined` at runtime despite the type saying `string`. This is a latent type-lie shared across `useMe`/`usePatchSettings`/poll; it happens to be benign only because no current reader consumes `access_token` from the `["me"]` cache.

**Fix:** Give `/api/me` its own response type without `access_token` (or make `access_token` optional on the shared type) so the cache shape is honest and a future consumer cannot be misled. The backend already models this correctly (`MeResponse` != `AuthResponse`); the FE should mirror it.

## Info

### IN-01: `PaymentStatus.PRE_CHECKOUT_APPROVED` is dead under ЮKassa

**File:** `backend/app/models/enums.py:90`

**Issue:** `PRE_CHECKOUT_APPROVED` is a Telegram-Stars-era pre-checkout state. The ЮKassa flow never uses it (created → paid/canceled/refunded). It is a harmless leftover but is now dead vocabulary in the payment state machine.

**Fix:** Leave a comment marking it Stars-legacy/unused under ЮKassa, or drop it in a later enum cleanup migration.

### IN-02: `WEBHOOK_SECRET` config field is retained but unused

**File:** `backend/app/core/config.py:62`

**Issue:** `WEBHOOK_SECRET` is explicitly documented as "NOT used by ЮKassa" and kept "for a possible future bot wiring." It is dead config surface for this phase. Acceptable per its comment, but it is one more unused knob operators can misconfigure and expect to matter.

**Fix:** Fine to keep given the explicit note; consider removing until the bot wiring actually lands (YAGNI).

### IN-03: `_handle_refund_succeeded` silently no-ops when the re-fetched refund lacks a `payment_id`

**File:** `backend/app/services/payments.py:770-783`

**Issue:** When a `refund.succeeded` re-fetch returns an object without a resolvable `payment_id`, the handler returns without reconciling and without any log (lines 773-775). This is intended (the admin path is the deterministic entrypoint), but a webhook refund that cannot be reconciled leaves no breadcrumb, so an entitlement that should have been clawed back can silently linger with zero observability.

**Fix:** Add a `logger.warning(...)` on the un-resolvable-refund branch so ops can detect and manually reconcile.

### IN-04: `create_payment` persists `confirmation_url = None` on a subscription/renewal-shaped response without surfacing the anomaly

**File:** `backend/app/services/payments.py:366-372` + `backend/app/api/payments.py:113-117`

**Issue:** `create_payment` sets `confirmation_url` from the response's `confirmation.confirmation_url` and the router returns `payment.confirmation_url or ""`. If ЮKassa ever returns a payment without a confirmation block on the interactive create path (misconfig, or an unexpected instant-capture), the FE receives `confirmation_url = ""`, and `ShopTariffs.buy` throws "missing confirmation_url" → generic failure with no server-side signal. The empty-string coalescing hides the root cause.

**Fix:** Log a warning in `create_payment` when the interactive (non-`payment_method_id`) create returns no confirmation URL, so the failure is diagnosable server-side.

### IN-05: Magic dismiss/poll timings are scattered literals across FE modules

**File:** `frontend/src/components/shop/ShopTariffs.tsx:40` (`SUCCESS_DISMISS_MS = 1400`), `frontend/src/hooks/usePayments.ts:26-27` (`POLL_INTERVAL_MS`/`POLL_MAX_ATTEMPTS`)

**Issue:** The poll budget (2s × 10 = 20s) and the 1.4s success dismiss are reasonable but are per-file literals. If ЮKassa webhook latency exceeds ~20s (not unusual for card 3-DS flows), the poll returns `false` and the honest-failure copy is shown even though the grant will arrive shortly after; the caller then relies on a later `useMe` refetch. This is a UX tuning risk, not a correctness bug.

**Fix:** Consider centralizing the payment-flow timings and/or widening the poll budget for the subscription/3-DS case; document the "poll may time out before a slow webhook" behavior.

### IN-06: `is_from_yookassa` trusts the left-most `X-Forwarded-For` with no proxy-count validation

**File:** `backend/app/api/payments.py:123-134`

**Issue:** `_client_ip` returns the left-most `X-Forwarded-For` entry, which is client-controllable unless the reverse proxy strips/rewrites inbound XFF. The docstring acknowledges this is defence-in-depth and the re-fetch is the real guard (audited), so this is out of the security-re-litigation scope — noting only as a robustness reminder: the allowlist is only meaningful if timeweb is configured to overwrite (not append) XFF. No change required if the deploy guarantees that.

---

_Reviewed: 2026-07-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

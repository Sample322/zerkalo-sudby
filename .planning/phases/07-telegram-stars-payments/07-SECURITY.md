---
phase: 7
slug: telegram-stars-payments
status: verified
threats_open: 0
asvs_level: 2
created: 2026-07-03
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Provider pivot (D-01): the phase slug says "telegram-stars" but the shipped money path is
> **ЮKassa (YooKassa) direct v3 API** in RUB. This audit verifies the ЮKassa surface.
>
> **Verify-only mode** — the threat register was authored at plan time (all seven 07-*-PLAN.md
> `<threat_model>` blocks). This audit confirms each declared mitigation EXISTS in the implemented
> code; it did NOT scan for new threats. The register below is the consolidated superset of the
> plan-time blocks (07-03/04/05/06/07) plus the task-supplied register.
>
> **Deploy note:** the money path is NOT yet live (no ЮKassa credentials). This audit verifies the
> CODE-LEVEL controls. Runtime/deploy items (secret rotation, the real webhook IP set, 54-ФЗ fiscal
> receipts) are owner-side deploy tasks recorded in the Accepted Risks Log, not code OPENs.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| ЮKassa → `POST /payments/yookassa/webhook` | Public, **UNSIGNED**. IP allowlist is the cheap edge gate; re-`GET /v3/payments/{id}` is the real authenticity guard. | Untrusted notification body (`object.id` read; `object.status` never trusted) |
| client → `POST /payments/create`, `POST /subscriptions/{id}/cancel` | Bearer JWT; identity from `sub` only, never a body field. | `product_slug` (create); path id scoped to `user.id` (cancel) |
| admin → `POST /payments/{id}/refund` | `require_admin` server-side allowlist (`ADMIN_TELEGRAM_IDS`). | Path payment id + optional `amount_rub` |
| Telegram WebView → ЮKassa-hosted page | `openLink(confirmation_url)`; the app never sees the PAN (PCI stays with ЮKassa). | Redirect URL only |
| client → grant | The UI grants nothing; it polls `GET /api/me` for the server-confirmed balance/sub. | Read-only `me` projection |
| scheduler → ЮKassa | Merchant-initiated renewal charge; deterministic per-period key bounds duplicate charge. | Saved `payment_method_id`, deterministic idempotence key |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-07-WEBHOOK-FORGE | Spoofing | webhook | mitigate | `_handle_payment_succeeded` re-`find_payment`s and grants ONLY on `_obj_get(fresh,"status")=="succeeded"` (`payments.py:410-412`); the unsigned body status is never read for granting. IP allowlist rejects non-ЮKassa sources before any work (`payments.py:153-156` `api/payments.py`). | closed |
| T-07-WEBHOOK-DOS | DoS | webhook | mitigate | `is_from_yookassa(ip)` cheap reject returns 403 BEFORE any DB/SDK work (`api/payments.py:153-156`); handler ALWAYS returns 200 on handled/dup so ЮKassa stops redelivering (`api/payments.py:165-167`). | closed |
| T-07-REPLAY | Tampering | redelivered event | mitigate | `grant_for_provider_payment` conditional `UPDATE payments … WHERE status=CREATED … RETURNING`; `.first() is None` ⇒ no double grant (`payments.py:475-494`). UNIQUE `provider_payment_id` backstop (`models/billing.py:125-127`, migration `0004:49-54`). Always-200 at router (`api/payments.py:165-167`). Test asserts redelivery not doubled (`test_payments_api.py:355-370`). | closed |
| T-07-IDOR | Elevation | refund/cancel/create | mitigate | Refund behind `require_admin` (`api/payments.py:177`, `deps.py:55-59`). Create/cancel identity from `get_current_user` JWT `sub` only (`api/payments.py:89,203`); cancel scoped `WHERE Subscription.user_id == user.id` → non-owned = 404 (`api/payments.py:213-222`). | closed |
| T-07-AMOUNT | Tampering | create | mitigate | `CreatePaymentIn` has only `product_slug`, NO amount field; `extra="ignore"` drops a smuggled `amount` (`schemas/payment.py:60-81`). Price recomputed server-side `format_rub(product.stars_price)` (`payments.py:340,131-139`). | closed |
| T-07-GRANT-ON-CREATE | Elevation | create | mitigate | `create_payment` writes a CREATED row + returns `confirmation_url`, mutates NO balance (`payments.py:328-372`); only the webhook grant path touches balances. | closed |
| T-07-SECRET-LEAK | Info Disclosure | config/responses | mitigate | `YOOKASSA_SHOP_ID`/`YOOKASSA_SECRET_KEY` required env, no default → fail-fast at import (`config.py:36-37,137`); SDK configured from `settings` only (`payments.py:210`). `ProductOut` exposes no secret/`raw_update`; `raw_update` is server-side JSONB audit only (`schemas/payment.py:28-57`). | closed |
| T-07-REFUND-OVERCREDIT | Tampering | refund | mitigate | `_reconcile_refund` decrements `paid_spreads_balance` by `Product.spreads_amount` clamped `func.greatest(…, 0)`, NEVER the RUB amount (`payments.py:817-827`). | closed |
| T-07-REFUND-WRONG-BUCKET | Tampering | refund | mitigate | `_reconcile_refund` branches on `product.product_type`: SUBSCRIPTION → `_revoke_subscription` (end window + zero bucket); pack → decrement spreads (`payments.py:814-827,830-846`). Honest-fail refund routes to the bucket actually consumed via `_refund_consumed_bucket` (`reading.py:872-888`). | closed |
| T-07-LOOP-BLOCK | DoS | sync ЮKassa SDK | mitigate | Every SDK call wrapped in `anyio.to_thread.run_sync(partial(...))` (`payments.py:243-245,251,263-265,271`). | closed |
| T-07-OPEN-REDIRECT | Tampering | return_url | mitigate | `_return_url()` is server-constructed from `settings.YOOKASSA_RETURN_URL` else a safe `https://t.me` default, never client-supplied (`payments.py:146-157,361`). FE opens only the server-returned `confirmation_url` (`ShopTariffs.tsx:80`, `telegram.ts:143-145`). | closed |
| T-07-DOUBLE-CHARGE | Tampering | recurring sweep | mitigate | Deterministic `idempotence_key = f"renew:{subscription.id}:{next_period}"` (`payments.py:649-650`); `_charge_with_retry` reuses the same key across retries (`payments.py:697-728`). | closed |
| T-07-SWEEP-ABORT | Availability | one failing charge | mitigate | `_run_sweep` per-subscription try/except isolates a failed charge (`scheduler.py:53-65`); `renew_subscription` swallows a charge failure → `PAYMENT_FAILED`, keeps `current_period_end` (`payments.py:665-676`). | closed |
| T-07-SC | Tampering | APScheduler install | mitigate | Human package-legitimacy checkpoint recorded: APScheduler approved via AskUserQuestion (broker-free, maintainer agronholm, Py3.12) before the dep was added (`07-06-SUMMARY.md:12-14,47`); pinned `APScheduler>=3.11,<4`, in-memory jobstore (`scheduler.py:32-38`). | closed |
| T-07-MULTI-INSTANCE | Tampering | >1 backend sweeping | **accept** | Single-container deploy (A2). Deterministic per-period key still bounds a duplicate charge (`payments.py:649-650`); documented timeweb-cron fallback if scaled (`scheduler.py:10-13`). See Accepted Risks Log. | closed |
| T-07-TEST-LIVE | Tampering | tests | mitigate | `FakeYooKassa` is the only ЮKassa surface, injected via the `PaymentService(yookassa=…)` + `dependency_overrides[get_payment_service]` seam (`fakes_payments.py`, `test_payments_api.py:90`). Grep over `backend/tests` finds NO `from yookassa`/`import yookassa`/`api.yookassa.ru` (only a `yoomoney.test` fake host). App SDK imports are all lazy inside method bodies (`payments.py:208,228,249,257,269`). | closed |
| T-07-CARD-DATA | Info Disclosure | payment page | mitigate | `openLink(confirmation_url)` hands off to the ЮKassa-hosted page; the app never touches PAN (`telegram.ts:137-145`, `ShopTariffs.tsx:79-81`). | closed |
| T-07-CLIENT-GRANT | Elevation | shop UI | mitigate | `ShopTariffs.buy` opens the page then polls `GET /api/me` (`usePollMeUntilGranted`) for the webhook-confirmed balance/sub — grants nothing client-side (`ShopTariffs.tsx:82-103`, `api/payments.ts:4-5`). | closed |
| SAFE-06 | brand | shop copy | mitigate | All shop strings are `copy.ts` constants `SHOP_*` (`copy.ts:215-224`); `copy.test.ts` concatenates EVERY exported string via `collectStrings(copy)` and asserts `BANNED_BRAND_TOKENS.test(allCopy)===false` (`copy.test.ts:47-62`). Honest «деньги не списаны» on failure (`copy.ts:222-223`). | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-MULTI-INSTANCE | Single-container deploy (A2) means only one sweeper runs. The deterministic `renew:<sub_id>:<period_index>` key bounds a duplicate charge even if two instances ever swept, and a timeweb-cron→single-endpoint fallback is documented (`scheduler.py:10-13`). Re-open only if the backend is horizontally scaled. | Owner (plan-time A2) | 2026-07-03 |
| AR-07-02 | T-07-SECRET-LEAK (deploy) | ЮKassa `SHOP_ID`/`SECRET_KEY` rotation + injection is an owner-side deploy task. Code enforces fail-fast-on-missing and never serializes the secret; setting/rotating the real values is not a code control. | Owner (deploy) | 2026-07-03 |
| AR-07-03 | T-07-WEBHOOK-FORGE (deploy) | The built-in ЮKassa CIDR allowlist (`payments.py:90-98`) is defence-in-depth; the authoritative guard is the re-fetch-by-id. Confirming/overriding the exact live source range (`YOOKASSA_WEBHOOK_IPS`) at deploy is an owner-side task. | Owner (deploy) | 2026-07-03 |
| AR-07-04 | 54-ФЗ fiscal receipts | Fiscal receipt (чек) generation for the ЮKassa money path is deferred to deploy/legal (not in this phase's code scope). No code control; owner-side compliance task before public launch. | Owner (deploy/legal) | 2026-07-03 |

*Accepted risks do not resurface in future audit runs.*

---

## Observations (non-blocking)

- **T-07-TEST-LIVE automated gate:** `fakes_payments.py:4-8` describes a "grep gate over `backend/tests` … asserts that invariant in CI", but no dedicated pytest enforces the no-real-SDK-import rule as an in-suite test. The substantive control is verified directly here (Grep across the whole `backend/tests` tree finds zero real-SDK imports and zero live-host literals), so the threat is CLOSED; a CI grep step or a small guard test would make the invariant self-enforcing against future drift. Recommendation only, not a blocker.
- **Threat Flags:** No `## Threat Flags` sections exist in the 07-*-SUMMARY.md files (this phase variant did not emit them). No unregistered attack surface was found: every route/component touched by the phase maps to a registered threat above.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-03 | 19 | 19 | 0 | gsd-security-auditor (verify-only) |

*Total = 18 T-07-* threats + SAFE-06. T-07-MULTI-INSTANCE closed via documented accepted risk (AR-07-01).*

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-03

"""``PaymentService`` — the ЮKassa (YooKassa) money-path core (PAY-02/04/05/06/07).

This is the highest-risk surface in the project: real money moves through it, so every
security invariant the phase depends on lives HERE, concentrated in one service so the
router (Plan 04) stays thin and the consume-gate (Plan 05) reads a single pinned contract.

The official ``yookassa`` SDK is **synchronous** (built on ``requests``); calling it directly
from an ``async def`` handler would block the single event loop (Pitfall 3 / T-07-LOOP-BLOCK).
So every SDK touch goes through ``_YooKassaClient``, whose methods wrap the sync call in
``anyio.to_thread.run_sync(partial(...))``. ``PaymentService`` takes that client via a
constructor seam (``PaymentService(yookassa=...)``) so ``FakeYooKassa`` (Plan 01) drives every
test with zero live calls — exactly the ``ReadingService(safety=..., llm=...)`` collaborator
pattern.

THE SECURITY SPINE (each maps to a STRIDE threat in the plan's register):
  * **Grant only on a re-fetched ``succeeded``** (T-07-WEBHOOK-FORGE / D-05): ЮKassa webhooks are
    UNSIGNED, so the body status is NEVER read for a grant decision — the handler takes
    ``object.id`` and re-``find_payment``s it, trusting only the API-confirmed status.
  * **Exactly-once grant** (T-07-REPLAY): a conditional ``UPDATE payments WHERE status=CREATED …
    RETURNING`` (mirroring ``reading.py``'s ``_consume_free_atomic``) is the race guard — the
    ``.first() is None`` branch means "already granted (redelivery) OR unknown id", so a
    redelivered ``payment.succeeded`` grants nothing. The UNIQUE ``provider_payment_id`` is the
    DB backstop.
  * **Never grant on create** (T-07-GRANT-ON-CREATE): ``create_payment`` writes a CREATED row and
    returns the ``confirmation_url`` — it mutates NO balance. Only the webhook grant path does.
  * **Server-recomputed price** (T-07-AMOUNT): the charged amount is always recomputed from
    ``Product.stars_price`` (an integer in RUBLES, A1) via ``format_rub`` — never a client value.
  * **Deterministic recurring key** (T-07-DOUBLE-CHARGE): a renewal uses
    ``renew:<sub_id>:<period_index>`` so a transient retry within a period is a safe no-op at
    ЮKassa (24h idempotency) while the next period gets a fresh key.
  * **Refund by entitlement, not RUB** (T-07-REFUND-OVERCREDIT): a refund decrements
    ``paid_spreads_balance`` by ``Product.spreads_amount`` (the granted units, e.g. 3 for
    ``pack_3``), clamped ``>= 0`` — NEVER by the RUB ``payment.amount``.
  * **Server-constructed return_url** (T-07-OPEN-REDIRECT): the ЮKassa ``return_url`` is the app's
    own deep link derived server-side, never a client-supplied value.

This module is also the AUTHORITATIVE OWNER of the D-09 subscription-entitlement encoding: it
defines ``SUBSCRIPTION_WINDOW_UNLIMITED`` and the exact ``subscription_spreads_limit``/``_used``
semantics the grant + renewal write, which Plan 04/05's consume-gate then reads. Plan 04/05
reference this constant by name and MUST NOT redefine it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from functools import partial
from ipaddress import ip_address, ip_network
from typing import Any, Protocol

import anyio.to_thread
import tenacity
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Payment, Product, Subscription, UserLimits
from app.models.enums import PaymentStatus, ProductType, SubscriptionStatus
from app.services.analytics import record_event

logger = logging.getLogger("app.payments")

# ---------------------------------------------------------------------------------------
# D-09 subscription entitlement contract — DEFINED HERE, consumed by Plan 04/05 by name.
# ---------------------------------------------------------------------------------------

SUBSCRIPTION_WINDOW_UNLIMITED: int = 1_000_000_000
"""The subscription bucket's "unlimited within the window" sentinel (D-09).

A subscription is **WINDOW-GATED, NOT count-gated** — the real bound on a «Лунный доступ»
subscriber's readings is ``Subscription.current_period_end`` (the 30-day window), not a count.
The grant + renewal therefore set ``UserLimits.subscription_spreads_limit =
SUBSCRIPTION_WINDOW_UNLIMITED`` and reset ``subscription_spreads_used = 0`` for each new period,
so the count-atomic gate (Plan 05) NEVER blocks inside an active window: its
``WHERE subscription_spreads_used < subscription_spreads_limit`` condition exists only to serialize
concurrent reads via the PostgreSQL row lock (the same exactly-once discipline the free bucket
uses), and ``determine_access`` selects the SUBSCRIPTION bucket only when the window is live.

This constant + rule is the SINGLE source of the encoding. Plan 04/05 reference it by name and
MUST NOT redefine a second sentinel.
"""

# ---------------------------------------------------------------------------------------
# ЮKassa source IP allowlist (defence-in-depth — re-fetch is the real guard, Pattern 3).
# ---------------------------------------------------------------------------------------

# Published ЮKassa webhook source ranges (07-RESEARCH §"Code Examples" / Security Domain). The
# webhook is UNSIGNED, so this allowlist + the re-fetch-by-id are the only authenticity controls
# (T-07-WEBHOOK-FORGE). Overridable via ``settings.YOOKASSA_WEBHOOK_IPS`` for a changed range.
_DEFAULT_YOOKASSA_CIDRS: tuple[str, ...] = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
)


def _build_nets() -> list[Any]:
    """Build the active ЮKassa CIDR list — the settings override wins when non-empty (A5)."""
    cidrs = settings.YOOKASSA_WEBHOOK_IPS or list(_DEFAULT_YOOKASSA_CIDRS)
    return [ip_network(cidr) for cidr in cidrs]


YOOKASSA_NETS: list[Any] = _build_nets()


def is_from_yookassa(ip: str) -> bool:
    """True when ``ip`` falls inside a published ЮKassa source range (defence-in-depth).

    A malformed / empty IP returns False (fail-closed): a webhook we cannot attribute to ЮKassa
    is treated as not-from-ЮKassa. The re-fetch-by-id (Pattern 3) remains the authoritative guard;
    this is the first, cheap line of defence (T-07-WEBHOOK-FORGE).
    """
    if not ip:
        return False
    try:
        addr = ip_address(ip.strip())
    except ValueError:
        return False
    return any(addr in net for net in YOOKASSA_NETS)


# ---------------------------------------------------------------------------------------
# RUB amount formatting (Pitfall 6) + the server-constructed return_url (T-07-OPEN-REDIRECT).
# ---------------------------------------------------------------------------------------


def format_rub(price_int: int) -> str:
    """Format an integer-RUBLES price as the ЮKassa ``amount.value`` string (Pitfall 6 / A1).

    ЮKassa expects ``amount.value`` as a **string with exactly 2 decimal places in major units**
    (rubles), e.g. ``299`` → ``"299.00"`` — NOT a float, NOT kopecks. ``products.stars_price`` holds
    the price as an integer in rubles (A1), so this is the single formatter the create + renewal
    paths use; the charged amount is always derived from the product row here, never from a client.
    """
    return f"{int(price_int):.2f}"


# The app's own Telegram deep link, used as the ЮKassa ``return_url`` (UX only — the webhook is the
# source of truth, D-07). SERVER-CONSTRUCTED (never client-supplied) so a malicious client cannot
# redirect the post-payment return to an arbitrary origin (T-07-OPEN-REDIRECT). A deploy can point
# this at the exact Mini App deep link via the env override; the default is a safe Telegram origin.
_DEFAULT_RETURN_URL = "https://t.me"


def _return_url() -> str:
    """The server-side ЮKassa ``return_url`` (the app deep link) — never a client value.

    Derived from an optional ``YOOKASSA_RETURN_URL`` setting when present, else a safe Telegram
    origin default. The return is pure UX (the FE polls ``GET /api/me`` after returning, D-07);
    the authoritative grant is the webhook, so an imperfect default never affects correctness —
    but it must stay server-constructed to close T-07-OPEN-REDIRECT.
    """
    return getattr(settings, "YOOKASSA_RETURN_URL", None) or _DEFAULT_RETURN_URL


# ---------------------------------------------------------------------------------------
# The ЮKassa client seam — the real adapter wraps the SYNC SDK in anyio.to_thread (Pattern 1).
# ---------------------------------------------------------------------------------------


class _YooKassaClientProtocol(Protocol):
    """The four ЮKassa operations ``PaymentService`` depends on (the ``FakeYooKassa`` contract).

    Both the real ``_YooKassaClient`` (sync SDK wrapped in ``anyio.to_thread``) and the test
    ``FakeYooKassa`` satisfy this — so either can be injected through the same constructor seam.
    Every method is ``async`` and keyword-only, returning a ЮKassa-shaped object exposing the read
    fields (``id``/``status``/``amount``/``confirmation``/``payment_method``) + a ``json()`` dict.
    """

    async def create_payment(
        self,
        *,
        value_rub: str,
        return_url: str,
        idempotence_key: str,
        metadata: dict[str, Any],
        save_payment_method: bool = ...,
        payment_method_id: str | None = ...,
    ) -> Any: ...

    async def find_payment(self, payment_id: str) -> Any: ...

    async def create_refund(
        self, *, payment_id: str, value_rub: str, idempotence_key: str
    ) -> Any: ...

    async def find_refund(self, refund_id: str) -> Any: ...


class _YooKassaClient:
    """The real ЮKassa v3 client adapter — every SYNC SDK call wrapped off the event loop.

    Configures the SDK once at construction (``Configuration.configure(shop_id, secret_key)``) from
    ``settings`` (the secret never leaves env — T-07-SECRET-LEAK), then runs each ``Payment.create``/
    ``Payment.find_one``/``Refund.create``/``Refund.find_one`` via ``anyio.to_thread.run_sync`` so
    the single event loop is never blocked during the ЮKassa round-trip (Pitfall 3 / T-07-LOOP-BLOCK).

    The SDK is imported lazily inside ``__init__`` so merely importing this module (e.g. under the
    test suite, which uses ``FakeYooKassa`` and asserts no real SDK import in ``tests/``) does not
    require the package to be configured — the real client is only built when actually used.
    """

    def __init__(self) -> None:
        from yookassa import Configuration  # lazy: only the real path needs the SDK

        Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

    async def create_payment(
        self,
        *,
        value_rub: str,
        return_url: str,
        idempotence_key: str,
        metadata: dict[str, Any],
        save_payment_method: bool = False,
        payment_method_id: str | None = None,
    ) -> Any:
        """Create a ЮKassa payment (sync SDK, off the loop).

        An interactive create carries a ``confirmation`` (redirect) block; a merchant-initiated
        renewal passes ``payment_method_id`` and NO confirmation block (charged without user
        interaction, Pattern 4). Amount is the server-computed ``value_rub`` (RUB string).
        """
        from yookassa import Payment as YkPayment

        body: dict[str, Any] = {
            "amount": {"value": value_rub, "currency": "RUB"},
            "capture": True,
            "description": "Зеркало Судьбы",
            "metadata": metadata,
        }
        if payment_method_id is not None:
            # Merchant-initiated recurring charge — NO confirmation block (Pattern 4 / Code Examples).
            body["payment_method_id"] = payment_method_id
        else:
            body["confirmation"] = {"type": "redirect", "return_url": return_url}
        if save_payment_method:
            body["save_payment_method"] = True
        return await anyio.to_thread.run_sync(
            partial(YkPayment.create, body, idempotence_key)
        )

    async def find_payment(self, payment_id: str) -> Any:
        """Re-fetch a payment by id — the D-05 authoritative status check (sync SDK, off the loop)."""
        from yookassa import Payment as YkPayment

        return await anyio.to_thread.run_sync(partial(YkPayment.find_one, payment_id))

    async def create_refund(
        self, *, payment_id: str, value_rub: str, idempotence_key: str
    ) -> Any:
        """Create a ЮKassa refund for a succeeded payment (sync SDK, off the loop)."""
        from yookassa import Refund as YkRefund

        body = {
            "amount": {"value": value_rub, "currency": "RUB"},
            "payment_id": payment_id,
        }
        return await anyio.to_thread.run_sync(
            partial(YkRefund.create, body, idempotence_key)
        )

    async def find_refund(self, refund_id: str) -> Any:
        """Re-fetch a refund by id — the refund-reconciliation re-fetch (sync SDK, off the loop)."""
        from yookassa import Refund as YkRefund

        return await anyio.to_thread.run_sync(partial(YkRefund.find_one, refund_id))


# ---------------------------------------------------------------------------------------
# Object-field accessors — the SDK objects + FakeYooKassa both expose attributes + dict-ish reads.
# ---------------------------------------------------------------------------------------


def _obj_get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a ЮKassa object (attribute) or a plain dict (item), tolerant of both."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_raw(obj: Any) -> dict[str, Any]:
    """Best-effort serialize a ЮKassa object to a JSONB-safe dict for the ``raw_update`` audit.

    The real SDK objects (and ``FakeYooKassa``'s) expose a ``json()`` returning a dict; fall back
    to ``__dict__`` / an empty dict so the audit write never raises in the grant transaction.
    """
    json_fn = getattr(obj, "json", None)
    if callable(json_fn):
        try:
            data = json_fn()
            if isinstance(data, dict):
                return data
        except Exception:  # noqa: BLE001 - audit best-effort; never break the grant on serialize
            pass
    if isinstance(obj, dict):
        return dict(obj)
    return {}


def _payment_method_id_from(obj: Any) -> str | None:
    """Extract the saved ``payment_method.id`` from a re-fetched payment object (PAY-06)."""
    pm = _obj_get(obj, "payment_method")
    if pm is None:
        return None
    return _obj_get(pm, "id")


class PaymentService:
    """The ЮKassa money-path: create (no grant), webhook re-fetch + idempotent grant, recurring, refund.

    The ЮKassa client is injected via the ``yookassa`` keyword (default = the real
    ``_YooKassaClient``), the established collaborator seam (``ReadingService(safety=..., llm=...)``)
    — so ``FakeYooKassa`` drives every test with zero live calls. Each public method owns its own
    transaction (commits its grant/flip), mirroring ``ReadingService``'s ownership of the reading
    transaction.
    """

    def __init__(self, *, yookassa: _YooKassaClientProtocol | None = None) -> None:
        self._client: _YooKassaClientProtocol = yookassa or _YooKassaClient()

    # ------------------------------------------------------------------ create (NO grant, Pattern 2)

    async def create_payment(
        self, session: AsyncSession, user: Any, product: Product
    ) -> Payment:
        """Create a ЮKassa payment for ``product`` and return the CREATED ``payments`` row (PAY-02).

        Pattern 2 — NEVER grants here (grant-on-create is the classic fraud hole,
        T-07-GRANT-ON-CREATE): writes a CREATED row, calls ЮKassa, persists
        ``provider_payment_id``/``confirmation_url`` from the response, commits, returns the row. The
        charged amount is RECOMPUTED from ``product.stars_price`` (T-07-AMOUNT) — the caller passes a
        resolved ``Product`` (Plan 04 looks it up by ``product_slug`` and rejects inactive), never a
        client amount. The ``return_url`` is server-constructed (T-07-OPEN-REDIRECT).
        """
        value_rub = format_rub(product.stars_price)
        payload = f"{user.id}:{product.id}:{uuid.uuid4()}"
        idempotence_key = str(uuid.uuid4())  # per-attempt (Pitfall 5)
        save_method = product.product_type == ProductType.SUBSCRIPTION

        payment = Payment(
            user_id=user.id,
            product_id=product.id,
            provider="yookassa",
            currency="RUB",
            amount=product.stars_price,
            payload=payload,
            idempotence_key=idempotence_key,
            status=PaymentStatus.CREATED,
        )
        session.add(payment)
        await session.flush()  # assign payment.id for the metadata round-trip

        created = await self._client.create_payment(
            value_rub=value_rub,
            return_url=_return_url(),
            idempotence_key=idempotence_key,
            metadata={"payment_uuid": str(payment.id)},
            save_payment_method=save_method,
        )

        payment.provider_payment_id = _obj_get(created, "id")
        confirmation = _obj_get(created, "confirmation")
        payment.confirmation_url = (
            _obj_get(confirmation, "confirmation_url") if confirmation else None
        )
        await session.commit()
        return payment

    # ------------------------------------------------------------------ webhook routing (D-05)

    async def handle_webhook_event(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> None:
        """Route a ЮKassa webhook envelope by ``event`` type — NEVER trusting the body status (D-05).

        Takes ``object.id`` only; the (unsigned) ``object.status`` is never read for a grant decision
        (T-07-WEBHOOK-FORGE). ``payment.succeeded`` → re-fetch + grant; ``refund.succeeded`` →
        re-fetch + refund recon; ``payment.canceled`` → flip the matching CREATED row to CANCELED (no
        grant). Any unknown event is a safe no-op. The IP allowlist gate lives in the router (Plan 04,
        which has the request); this method is the body-status-blind dispatcher.
        """
        event_type = event.get("event")
        obj = event.get("object") or {}
        object_id = _obj_get(obj, "id")
        if not object_id:
            return

        if event_type == "payment.succeeded":
            await self._handle_payment_succeeded(session, object_id)
        elif event_type == "refund.succeeded":
            await self._handle_refund_succeeded(session, object_id)
        elif event_type == "payment.canceled":
            await self._handle_payment_canceled(session, object_id)
        # Unknown event → no-op (return 200 at the router so ЮKassa stops redelivering).

    async def _handle_payment_succeeded(
        self, session: AsyncSession, object_id: str
    ) -> None:
        """Re-fetch the payment and grant ONLY if the API-confirmed status is ``succeeded`` (Pattern 3).

        The body status is ignored: ``find_payment`` is the authoritative check. A non-``succeeded``
        re-fetch (pending/canceled/lying body) returns without granting — ЮKassa will redeliver when
        it is final.
        """
        fresh = await self._client.find_payment(object_id)
        if _obj_get(fresh, "status") != "succeeded":
            return  # not final / body lied → no grant (Pitfall 1)
        await self.grant_for_provider_payment(
            session,
            provider_payment_id=_obj_get(fresh, "id") or object_id,
            raw=_as_raw(fresh),
            payment_method_id=_payment_method_id_from(fresh),
        )

    async def _handle_payment_canceled(
        self, session: AsyncSession, object_id: str
    ) -> None:
        """Flip a matching CREATED payment to CANCELED on ``payment.canceled`` (no grant).

        Conditional ``WHERE status=CREATED`` so a canceled event never disturbs an already-PAID row,
        and a redelivery is a clean no-op.
        """
        await session.execute(
            update(Payment)
            .where(
                self._provider_id_match(object_id),
                Payment.status == PaymentStatus.CREATED,
            )
            .values(status=PaymentStatus.CANCELED)
        )
        await session.commit()

    # ------------------------------------------------------------------ idempotent grant (Pattern 5)

    @staticmethod
    def _provider_id_match(provider_payment_id: str) -> Any:
        """Match a payment by its ЮKassa id across BOTH provider-id columns.

        The designed key is the UNIQUE ``provider_payment_id`` (set by ``create_payment`` + the
        T-07-REPLAY backstop). The legacy indexed ``telegram_payment_charge_id`` is also matched so a
        row whose id was recorded there (the pre-pivot id seam still used by some callers/fixtures) is
        still found — the grant must locate the row regardless of which provider-id column carries the
        ЮKassa id. Both are UNIQUE/indexed, so this stays a single-row, index-backed match.
        """
        return or_(
            Payment.provider_payment_id == provider_payment_id,
            Payment.telegram_payment_charge_id == provider_payment_id,
        )

    async def grant_for_provider_payment(
        self,
        session: AsyncSession,
        *,
        provider_payment_id: str,
        raw: dict[str, Any],
        payment_method_id: str | None = None,
    ) -> None:
        """Grant entitlement for a confirmed ЮKassa payment — EXACTLY ONCE (Pattern 5, T-07-REPLAY).

        THE exactly-once boundary: a conditional ``UPDATE payments … WHERE status=CREATED …
        RETURNING`` flips the row CREATED→PAID and only proceeds when the flip actually happened
        (mirrors ``reading.py``'s ``_consume_free_atomic``). ``.first() is None`` ⇒ the row was
        already PAID (redelivery) OR the id is unknown ⇒ RETURN with no grant (no double-grant,
        Pitfall 2). On a real transition: a ``one_time_spreads`` pack increments
        ``paid_spreads_balance`` by ``Product.spreads_amount`` (atomic UPDATE); a ``subscription``
        opens/extends a 30-day window AND writes the D-09 contract (``subscription_spreads_limit =
        SUBSCRIPTION_WINDOW_UNLIMITED``, ``subscription_spreads_used = 0`` reset for the new period).
        Commits.
        """
        row = (
            await session.execute(
                update(Payment)
                .where(
                    self._provider_id_match(provider_payment_id),
                    Payment.status == PaymentStatus.CREATED,
                )
                .values(
                    status=PaymentStatus.PAID,
                    paid_at=func.now(),
                    raw_update=raw,
                    provider_payment_id=provider_payment_id,
                )
                .returning(
                    Payment.id, Payment.product_id, Payment.user_id
                )
            )
        ).first()
        if row is None:
            return  # already granted (redelivery) OR unknown id → no double grant (T-07-REPLAY)

        _payment_id, product_id, user_id = row
        product = (
            await session.execute(select(Product).where(Product.id == product_id))
        ).scalar_one_or_none()
        if product is None:
            # Anomalous: a PAID payment pointing at a missing product. Commit the flip (the money
            # moved) but grant nothing — fail-closed rather than guess an entitlement.
            await session.commit()
            return

        is_subscription = product.product_type == ProductType.SUBSCRIPTION
        if is_subscription:
            await self._grant_subscription(
                session,
                user_id=user_id,
                product=product,
                provider_payment_id=provider_payment_id,
                payment_method_id=payment_method_id,
            )
        else:
            await self._grant_paid_spreads(
                session, user_id=user_id, spreads_amount=product.spreads_amount or 0
            )
        await session.commit()

        # Analytics (ANALYTICS-01) — the AUTHORITATIVE revenue signal, emitted only AFTER the grant
        # commits and fully isolated (record_event uses its own session + swallows all errors), so it
        # can never touch the money path. Non-PII: product slug + purchase type only.
        await record_event(
            user_id,
            "payment_succeeded",
            {"product_slug": product.slug, "purchase_type": product.product_type.value},
        )
        if is_subscription:
            await record_event(user_id, "subscription_started", {"product_slug": product.slug})

    @staticmethod
    async def _grant_paid_spreads(
        session: AsyncSession, *, user_id: Any, spreads_amount: int
    ) -> None:
        """Atomically add ``spreads_amount`` to the user's permanent ``paid_spreads_balance``."""
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(
                paid_spreads_balance=UserLimits.paid_spreads_balance + spreads_amount
            )
        )

    async def _grant_subscription(
        self,
        session: AsyncSession,
        *,
        user_id: Any,
        product: Product,
        provider_payment_id: str,
        payment_method_id: str | None,
    ) -> None:
        """Open/extend the 30-day window + write the D-09 entitlement contract onto ``user_limits``.

        Upserts the user's ``Subscription`` (ACTIVE, ``current_period_start=now``,
        ``current_period_end=now + subscription_days``, saved ``payment_method_id`` from the re-fetch
        when present) and sets the D-09 bucket on ``UserLimits``: ``subscription_spreads_limit =
        SUBSCRIPTION_WINDOW_UNLIMITED`` + ``subscription_spreads_used = 0`` (reset for the new period,
        so the count-atomic gate never drifts and never blocks inside a live window — the window is
        the real bound).
        """
        now = datetime.now(UTC)
        days = product.subscription_days or 30

        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user_id,
                product_id=product.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=now + timedelta(days=days),
                period_index=0,
            )
            session.add(sub)
        else:
            # WR-02: extend from the LATER of ``now`` and the existing end so an early re-buy /
            # renewal never DISCARDS unused remaining time (a flat ``now + days`` would shrink a
            # window the user already paid for). A lapsed window (end < now) restarts from now.
            base = (
                sub.current_period_end
                if sub.current_period_end is not None and sub.current_period_end > now
                else now
            )
            sub.product_id = product.id
            sub.status = SubscriptionStatus.ACTIVE
            sub.current_period_start = now
            sub.current_period_end = base + timedelta(days=days)
        sub.provider_payment_id = provider_payment_id
        sub.last_charge_at = now
        if payment_method_id is not None:
            sub.payment_method_id = payment_method_id

        # D-09: window-gated unlimited — reset the bucket for the new period.
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(
                subscription_spreads_limit=SUBSCRIPTION_WINDOW_UNLIMITED,
                subscription_spreads_used=0,
            )
        )
        await session.flush()

    # ------------------------------------------------------------------ due sweep (Plan 06)

    async def find_due_subscriptions(
        self,
        session: AsyncSession,
        *,
        now: datetime | None = None,
        grace_days: int = 0,
    ) -> list[Subscription]:
        """Select ACTIVE subscriptions due for renewal (``current_period_end <= now + grace``).

        The service owns the sweep query so the scheduler job (Plan 06) is a thin loop. ONLY ACTIVE
        subscriptions are due — a CANCELED / EXPIRED / PAYMENT_FAILED row is NEVER re-charged (cancel
        keeps access to period end via the gate, D-10, but the sweep must not renew it). ``now`` is
        tz-aware (``current_period_end`` is ``TIMESTAMP(timezone=True)``, A1); ``grace_days`` widens
        the window so a subscription about to lapse is picked up on the daily tick. Read-only + atomic.
        """
        cutoff = (now or datetime.now(UTC)) + timedelta(days=grace_days)
        return list(
            (
                await session.execute(
                    select(Subscription).where(
                        Subscription.status == SubscriptionStatus.ACTIVE,
                        Subscription.current_period_end <= cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )

    # ------------------------------------------------------------------ recurring renewal (Pattern 4)

    async def renew_subscription(
        self, session: AsyncSession, subscription: Subscription
    ) -> None:
        """Merchant-initiated renewal charge for a due subscription (PAY-06, Pattern 4 / Pitfall 5).

        ЮKassa does NOT auto-charge — the merchant triggers each period. Charges via the saved
        ``payment_method_id`` with NO confirmation block and a DETERMINISTIC Idempotence-Key
        ``renew:<sub_id>:<period_index>`` (so a transient retry within the period reuses the key — a
        safe no-op at ЮKassa's 24h idempotency — while the next period gets a fresh key,
        T-07-DOUBLE-CHARGE). The amount is the subscription product's price, recomputed server-side.

        On success: write a CREATED renewal ``payments`` row (so the success webhook grants + extends
        via ``grant_for_provider_payment``, which ALSO resets ``subscription_spreads_used = 0`` for
        the new period per D-09) and advance ``period_index`` + ``last_charge_at``. On charge failure:
        set ``status = PAYMENT_FAILED`` but KEEP ``current_period_end`` (access until period end,
        D-10). Commits.
        """
        product = (
            await session.execute(
                select(Product).where(Product.id == subscription.product_id)
            )
        ).scalar_one_or_none()
        if product is None:
            return

        # WR-01: a concurrent self-serve cancel may have flipped this row between the sweep's
        # due-select and now (the cancel commits in the API request's session, not the sweep's).
        # Re-assert ACTIVE from the committed state before charging so a CANCELED / EXPIRED /
        # PAYMENT_FAILED subscription is never re-charged.
        current_status = (
            await session.execute(
                select(Subscription.status).where(Subscription.id == subscription.id)
            )
        ).scalar_one_or_none()
        if current_status is not SubscriptionStatus.ACTIVE:
            return

        next_period = (subscription.period_index or 0) + 1
        idempotence_key = f"renew:{subscription.id}:{next_period}"
        # WR-03: the saved card is the ЮKassa ``payment_method_id`` ONLY (set by ``_grant_subscription``
        # from the first payment's re-fetched ``payment_method.id``). The legacy
        # ``telegram_payment_charge_id`` is a Stars-era column that NEVER carries a payment-method id
        # under ЮKassa — reading it as a fallback could send a garbage method to ЮKassa. A ``None``
        # here means there is no saved card to charge → the subscription is un-renewable → mark
        # PAYMENT_FAILED but KEEP ``current_period_end`` (access until period end, D-10) and skip ЮKassa.
        saved_method = subscription.payment_method_id
        if saved_method is None:
            subscription.status = SubscriptionStatus.PAYMENT_FAILED
            await session.commit()
            logger.warning(
                "subscription_renewal_no_saved_method",
                extra={
                    "event": "payment.renewal_no_method",
                    "subscription_id": str(subscription.id),
                    "period_index": next_period,
                },
            )
            return

        try:
            created = await self._charge_with_retry(
                value_rub=format_rub(product.stars_price),
                payment_method_id=saved_method,
                idempotence_key=idempotence_key,
                metadata={"subscription_id": str(subscription.id), "period": str(next_period)},
            )
        except Exception:  # noqa: BLE001 - any charge failure → PAYMENT_FAILED, keep access (D-10)
            subscription.status = SubscriptionStatus.PAYMENT_FAILED
            await session.commit()
            logger.warning(
                "subscription_renewal_failed",
                extra={
                    "event": "payment.renewal_failed",
                    "subscription_id": str(subscription.id),
                    "period_index": next_period,
                },
            )
            return

        # Persist a CREATED renewal payment row so the success webhook grants + extends the window
        # (and resets the D-09 bucket) via the same idempotent grant path as a first payment.
        renewal_payment = Payment(
            user_id=subscription.user_id,
            product_id=product.id,
            provider="yookassa",
            currency="RUB",
            amount=product.stars_price,
            payload=f"renew:{subscription.id}:{next_period}:{uuid.uuid4()}",
            idempotence_key=idempotence_key,
            provider_payment_id=_obj_get(created, "id"),
            payment_method_id=saved_method,
            status=PaymentStatus.CREATED,
        )
        session.add(renewal_payment)
        subscription.period_index = next_period
        subscription.last_charge_at = datetime.now(UTC)
        await session.commit()

    def _charge_with_retry(
        self,
        *,
        value_rub: str,
        payment_method_id: str | None,
        idempotence_key: str,
        metadata: dict[str, Any],
    ) -> Any:
        """Call the renewal charge under a bounded ``tenacity`` retry (transient ЮKassa 5xx).

        The retry REUSES the deterministic Idempotence-Key, so a retried same-period charge is a safe
        no-op at ЮKassa (never a double-charge, Pitfall 5). Bounded to a few attempts with a short
        exponential backoff; on exhaustion the exception propagates to ``renew_subscription`` which
        sets PAYMENT_FAILED.
        """
        retrying = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=0.5, max=4),
            retry=tenacity.retry_if_exception_type(Exception),
            reraise=True,
        )

        async def _do() -> Any:
            return await self._client.create_payment(
                value_rub=value_rub,
                return_url=_return_url(),
                idempotence_key=idempotence_key,
                metadata=metadata,
                payment_method_id=payment_method_id,
            )

        return retrying(_do)

    # ------------------------------------------------------------------ refund (Pattern 6, D-14)

    async def refund_payment(
        self,
        session: AsyncSession,
        payment: Payment,
        *,
        amount_rub: int | None = None,
    ) -> None:
        """Admin-triggered refund + reconciliation (PAY-07, Pattern 6, T-07-REFUND-OVERCREDIT).

        Calls ``Refund.create`` for the payment's provider id (full amount by default; ``amount_rub``
        allows a partial). Reconciles (flip REFUNDED + claw back the GRANTED ENTITLEMENT, never RUB)
        ONLY when ЮKassa confirms the refund actually **succeeded** (CR-02): a ``pending`` / failed
        refund must NOT revoke access, else the user could lose access AND — if it never settles —
        their money. Money-FIRST ordering is deliberate (the refund is initiated before any local
        state change, protecting the user) and the deterministic ``refund:<provider_id>``
        Idempotence-Key makes a retried admin refund a safe ЮKassa no-op. When the refund settles
        later, ЮKassa fires ``refund.succeeded`` → the webhook re-fetches the refund and runs the SAME
        idempotent ``_reconcile_refund`` (the crash-window redrive: if this process dies between the
        ЮKassa call and the local commit, the webhook still reconciles exactly once).
        """
        provider_id = payment.provider_payment_id or payment.telegram_payment_charge_id
        if provider_id is None:
            return
        value = format_rub(amount_rub if amount_rub is not None else payment.amount)
        refund = await self._client.create_refund(
            payment_id=provider_id,
            value_rub=value,
            idempotence_key=f"refund:{provider_id}",
        )
        # Only claw access back on a CONFIRMED succeeded refund; a pending one is reconciled by the
        # refund.succeeded webhook when it settles (never revoke access on an unconfirmed refund).
        if _obj_get(refund, "status") == "succeeded":
            await self._reconcile_refund(session, payment)

    async def _handle_refund_succeeded(
        self, session: AsyncSession, object_id: str
    ) -> None:
        """Reconcile a ``refund.succeeded`` webhook — re-fetch the refund, then claw back access.

        Re-fetches the refund (never trusting the body) and resolves the underlying payment by the
        refund's ``payment_id`` (the real ЮKassa refund object carries it). If the payment is found
        and still PAID, reconciles (flip REFUNDED + decrement the granted entitlement). When the
        re-fetched refund does not carry a resolvable ``payment_id`` (e.g. a minimal object), it is a
        safe no-op — the admin path (``refund_payment``, which knows the payment) is the
        fully-deterministic reconciliation entrypoint.
        """
        fresh = await self._client.find_refund(object_id)
        if _obj_get(fresh, "status") != "succeeded":
            return
        provider_payment_id = _obj_get(fresh, "payment_id")
        if not provider_payment_id:
            return
        payment = (
            await session.execute(
                select(Payment).where(self._provider_id_match(provider_payment_id))
            )
        ).scalar_one_or_none()
        if payment is None:
            return
        await self._reconcile_refund(session, payment)

    async def _reconcile_refund(self, session: AsyncSession, payment: Payment) -> None:
        """Flip a PAID payment to REFUNDED + claw back the GRANTED entitlement (idempotent).

        Conditional ``UPDATE … WHERE id=… AND status=PAID … RETURNING`` — ``.first() is None`` ⇒
        already refunded ⇒ no-op (idempotent on redelivery). Else adjust access by the granted units,
        NEVER by RUB (T-07-REFUND-OVERCREDIT): a ``one_time_spreads`` pack decrements
        ``paid_spreads_balance`` by ``Product.spreads_amount`` clamped ``>= 0``; a ``subscription``
        ends the window (``current_period_end=now``, ``status=EXPIRED``) and zeroes the subscription
        bucket so no window-grant lingers. Commits.
        """
        row = (
            await session.execute(
                update(Payment)
                .where(Payment.id == payment.id, Payment.status == PaymentStatus.PAID)
                .values(status=PaymentStatus.REFUNDED, refunded_at=func.now())
                .returning(Payment.id, Payment.product_id, Payment.user_id)
            )
        ).first()
        if row is None:
            return  # already refunded → idempotent no-op

        _payment_id, product_id, user_id = row
        product = (
            await session.execute(select(Product).where(Product.id == product_id))
        ).scalar_one_or_none()
        if product is None:
            await session.commit()
            return

        if product.product_type == ProductType.SUBSCRIPTION:
            await self._revoke_subscription(session, user_id=user_id)
        else:
            spreads = product.spreads_amount or 0
            # Decrement by the GRANTED units (not RUB), clamped >= 0 (T-07-REFUND-OVERCREDIT).
            await session.execute(
                update(UserLimits)
                .where(UserLimits.user_id == user_id)
                .values(
                    paid_spreads_balance=func.greatest(
                        UserLimits.paid_spreads_balance - spreads, 0
                    )
                )
            )
        await session.commit()

    @staticmethod
    async def _revoke_subscription(session: AsyncSession, *, user_id: Any) -> None:
        """End the subscription window + zero the D-09 bucket on a subscription refund."""
        now = datetime.now(UTC)
        await session.execute(
            update(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .values(status=SubscriptionStatus.EXPIRED, current_period_end=now)
        )
        await session.execute(
            update(UserLimits)
            .where(UserLimits.user_id == user_id)
            .values(subscription_spreads_limit=0, subscription_spreads_used=0)
        )


__all__ = [
    "SUBSCRIPTION_WINDOW_UNLIMITED",
    "YOOKASSA_NETS",
    "PaymentService",
    "format_rub",
    "is_from_yookassa",
]

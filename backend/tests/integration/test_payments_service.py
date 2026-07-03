"""PAY-04/05/06/07 (red stubs) — the ЮKassa grant / idempotency / recurring / refund SERVICE.

Target plan: **Plan 07-03** (``services/payments.py`` — the ЮKassa client wrapper + grant logic).
Each test below is the green target for one PAY-0x service behavior and ``xfail(strict=False)``
until Plan 03 lands (it **xpasses** the moment the symbol exists and behaves). The not-yet-existing
symbols (``PaymentService`` / ``grant_for_payment`` / the recurring + refund entrypoints) are
imported INSIDE each test body, mirroring the Phase-6 Wave-0 stub pattern, so a missing symbol
surfaces as the xfailed assertion — never a collection-time ``ImportError`` that would error the
whole module.

THE no-real-charge mandate (07-VALIDATION.md): every test drives ``FakeYooKassa`` (the only ЮKassa
surface in the suite — threat T-07-TEST-LIVE) injected via the future ``PaymentService`` constructor
seam; nothing reaches the live ЮKassa host. DB-touching tests run inside the transaction-isolated
``auth_session`` against the ``seeded_catalog`` (so the products/payments rows are real) and skip
cleanly when Postgres is unreachable — the suite stays green + collectable without ``docker compose
up``.

The exact ``PaymentService`` API is Plan 03's to finalize; these tests document the CONTRACT each
behavior must satisfy. Where a method name is Plan 03's choice, the test accesses it defensively
(``getattr``) and is xfail, so renaming during implementation turns the test green rather than
breaking collection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, User, UserLimits
from app.models.enums import PaymentStatus, ProductType, SubscriptionStatus
from tests.integration.conftest import FakeYooKassa

# ЮKassa webhook envelope (UNSIGNED — the service must re-fetch, never trust this body, D-05).
# Source: 07-RESEARCH.md §"Webhook notification envelope".
SUCCEEDED_EVENT = {
    "type": "notification",
    "event": "payment.succeeded",
    "object": {"id": "pay_test_000001", "status": "succeeded"},
}
REFUND_SUCCEEDED_EVENT = {
    "type": "notification",
    "event": "refund.succeeded",
    "object": {"id": "ref_test_000001", "status": "succeeded"},
}


# ---------------------------------------------------------------------------------------
# Helpers — real Product / Payment / UserLimits rows in the isolated session.
# ---------------------------------------------------------------------------------------


async def _make_user(session: AsyncSession, *, paid_balance: int = 0) -> User:
    """Insert a fresh user + a ``user_limits`` row (the paid/subscription buckets start empty)."""
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=3,
            free_used_this_week=3,  # free exhausted so the paid grant is what's observed
            paid_spreads_balance=paid_balance,
        )
    )
    await session.flush()
    return user


async def _make_product(
    session: AsyncSession,
    *,
    slug: str,
    product_type: ProductType = ProductType.ONE_TIME_SPREADS,
    price_rub: int = 169,
    spreads_amount: int | None = 3,
    subscription_days: int | None = None,
) -> Product:
    """Upsert an active ``products`` row (the server-authoritative price source, Pitfall 4).

    ``stars_price`` is repurposed as the RUB price (Assumption A1 — rubles-as-integer); the
    create path recomputes the charged amount from THIS column, never from a client field.

    Idempotent by ``slug``: ``seeded_catalog`` (a sibling fixture this test requests) seeds the
    real MVP catalog — which since Plan 07-02 includes packs (``pack_3``/``pack_10``) — so a blind
    INSERT of one of those slugs would violate the UNIQUE ``products.slug``. Reuse-and-overwrite
    the existing row instead so the test pins the exact price/spreads it asserts on, whether the
    slug was pre-seeded or is test-local (e.g. ``lunar_access``).
    """
    product = (
        await session.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if product is None:
        product = Product(slug=slug)
        session.add(product)
    product.title = f"Тест {slug}"
    product.product_type = product_type
    product.stars_price = price_rub
    product.spreads_amount = spreads_amount
    product.subscription_days = subscription_days
    product.is_active = True
    await session.flush()
    return product


async def _paid_balance(session: AsyncSession, user: User) -> int:
    limits = (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()
    return limits.paid_spreads_balance


async def _make_created_payment(
    session: AsyncSession,
    *,
    user: User,
    product: Product,
    provider_payment_id: str = "pay_test_000001",
) -> object:
    """Seed the CREATED ``payments`` row a webhook grant transitions (CREATED -> PAID).

    The grant is a conditional ``UPDATE payments WHERE status=CREATED ... RETURNING`` (the
    exactly-once race guard) — so a real CREATED row keyed by the provider id the webhook carries
    must exist for the grant to act on; this is the row ``create_payment`` writes before the user
    pays. ``provider_payment_id`` defaults to ``SUCCEEDED_EVENT.object.id`` and is stored on the
    legacy ``telegram_payment_charge_id`` seam (the id column the grant's ``_provider_id_match``
    resolves), mirroring the api-level webhook test's seed.
    """
    from app.models import Payment

    payment = Payment(
        user_id=user.id,
        product_id=product.id,
        provider="yookassa",
        currency="RUB",
        amount=product.stars_price,
        payload=f"pay-{uuid.uuid4()}",
        telegram_payment_charge_id=provider_payment_id,
        status=PaymentStatus.CREATED,
    )
    session.add(payment)
    await session.flush()
    return payment


def _make_service(fake: FakeYooKassa) -> object:
    """Build the (future) ``PaymentService`` with the fake ЮKassa client injected (the seam).

    Plan 03 finalizes the constructor; the established seam (mirroring ``ReadingService(safety=...,
    llm=...)``) is a keyword param for the client. This import is inside the call so a missing
    ``PaymentService`` surfaces as the xfailed assertion, not a collection error.
    """
    from app.services.payments import PaymentService

    return PaymentService(yookassa=fake)


def _resolve(obj: object, *names: str) -> object:
    """Return the first method on ``obj`` matching one of ``names`` (Plan 03 finalizes the name).

    The candidate name is a runtime variable (not a constant), so this stays clear of ruff B009 —
    these tests are xfail and must document the CONTRACT without hard-coding a method name Plan 03
    is free to choose. Raises ``AttributeError`` if none match (the xfailed assertion path).
    """
    for name in names:
        method = getattr(obj, name, None)
        if method is not None:
            return method
    raise AttributeError(f"{obj!r} has none of {names}")


# ---------------------------------------------------------------------------------------
# PAY-04 — grant on the re-fetched ``succeeded`` status (never the webhook body).
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-03 implements PaymentService grant-on-succeeded")
async def test_grant_paid_balance_on_succeeded(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """A re-fetched ``succeeded`` payment grants exactly the product's ``spreads_amount`` (PAY-04).

    The webhook handler must IGNORE the body status and re-fetch via ``find_payment`` (FakeYooKassa
    returns ``succeeded``), then increment ``paid_spreads_balance`` by the product's ``spreads_amount``
    inside one transaction. Builds a real CREATED ``payments`` row (Plan 03's create path is also
    red, so this seeds the row the grant transitions).
    """
    fake = FakeYooKassa(succeeded=True)
    service = _make_service(fake)
    user = await _make_user(auth_session, paid_balance=0)
    product = await _make_product(
        auth_session, slug="pack_3", spreads_amount=3, price_rub=169
    )
    # Seed the CREATED row the grant transitions (the provider id matches SUCCEEDED_EVENT.object.id).
    # The grant is a conditional CREATED->PAID flip, so it MUST have a real CREATED row to act on —
    # this is exactly the row create_payment would have written before the webhook arrives.
    await _make_created_payment(auth_session, user=user, product=product)

    # Plan 03 finalizes the entrypoint name; the contract is "handle a payment.succeeded event".
    handle = _resolve(service, "handle_webhook_event", "handle_payment_succeeded")
    await handle(auth_session, SUCCEEDED_EVENT)

    assert await _paid_balance(auth_session, user) == product.spreads_amount
    # The grant MUST have re-fetched the object (D-05) — never trusted the body.
    assert any(call[0] == "find_payment" for call in fake.recorded_calls)


@pytest.mark.xfail(strict=False, reason="Plan 07-03 grants only on the re-fetched succeeded status")
async def test_no_grant_on_unconfirmed_status(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """If the re-fetch returns ``pending``/``canceled``, NO balance change (Pitfall 1)."""
    fake = FakeYooKassa(next_status="canceled")  # re-fetch lies-vs-body → still no grant
    service = _make_service(fake)
    user = await _make_user(auth_session, paid_balance=0)
    await _make_product(auth_session, slug="pack_3", spreads_amount=3)

    handle = _resolve(service, "handle_webhook_event", "handle_payment_succeeded")
    await handle(auth_session, SUCCEEDED_EVENT)

    # Body said "succeeded"; the authoritative re-fetch said "canceled" → no grant.
    assert await _paid_balance(auth_session, user) == 0


# ---------------------------------------------------------------------------------------
# PAY-05 — idempotency: the SAME event twice grants exactly once (THE critical test).
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-03 makes the grant idempotent on redelivery")
async def test_grant_idempotent_on_redelivery(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """Delivering the SAME ``payment.succeeded`` twice grants exactly once (PAY-05, Pitfall 2).

    THE critical idempotency invariant: the conditional ``UPDATE ... WHERE status=CREATED ...
    RETURNING`` no-ops on the second delivery (the row is already PAID), so the balance is unchanged.
    ЮKassa retries until a 200, so redelivery is the norm — a double grant here is free money.
    """
    fake = FakeYooKassa(succeeded=True)
    service = _make_service(fake)
    user = await _make_user(auth_session, paid_balance=0)
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    # Seed the single CREATED row both deliveries target — the conditional CREATED->PAID flip
    # transitions it once; the redelivery finds it already PAID and grants nothing (exactly-once).
    await _make_created_payment(auth_session, user=user, product=product)

    handle = _resolve(service, "handle_webhook_event", "handle_payment_succeeded")
    await handle(auth_session, SUCCEEDED_EVENT)
    granted_once = await _paid_balance(auth_session, user)
    # Second (duplicate) delivery of the identical event.
    await handle(auth_session, SUCCEEDED_EVENT)
    granted_twice = await _paid_balance(auth_session, user)

    assert granted_once == product.spreads_amount
    assert granted_twice == granted_once  # NOT doubled — exactly-once grant


# ---------------------------------------------------------------------------------------
# PAY-06 — recurring renewal uses a DETERMINISTIC per-period Idempotence-Key (Pitfall 5).
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-03 implements the recurring renewal charge")
async def test_recurring_charge_uses_deterministic_key(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """A renewal charges via the saved method with key ``renew:<sub_id>:<period_index>`` (PAY-06).

    The merchant-initiated renewal calls ``create_payment`` with a ``payment_method_id`` set, NO
    confirmation block, and a DETERMINISTIC Idempotence-Key ``renew:<sub_id>:<period_index>`` — so a
    transient retry within the period reuses the key (safe no-op) while the next period gets a new
    key (Pitfall 5). The amount is the subscription product's price, recomputed server-side.
    """
    from app.models import Subscription

    fake = FakeYooKassa(succeeded=True)
    service = _make_service(fake)
    user = await _make_user(auth_session)
    product = await _make_product(
        auth_session,
        slug="lunar_access",
        product_type=ProductType.SUBSCRIPTION,
        price_rub=299,
        spreads_amount=None,
        subscription_days=30,
    )
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=user.id,
        product_id=product.id,
        telegram_payment_charge_id="pm_test_saved_0001",  # the saved payment_method_id seam
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=30),
        current_period_end=now,  # due now → the sweep charges it
    )
    auth_session.add(sub)
    await auth_session.flush()

    # Plan 03 finalizes the renewal entrypoint name; the contract is "charge a due subscription".
    charge = _resolve(service, "charge_renewal", "renew_subscription")
    await charge(auth_session, sub)

    create_calls = [c for c in fake.recorded_calls if c[0] == "create_payment"]
    assert create_calls, "the renewal must call create_payment with the saved method"
    kwargs = create_calls[-1][1]
    assert kwargs["payment_method_id"] == "pm_test_saved_0001"  # merchant-initiated, saved card
    assert kwargs["idempotence_key"].startswith(f"renew:{sub.id}:")  # deterministic per period
    # Server-authoritative amount — the product's RUB price formatted to 2 decimals.
    assert kwargs["value_rub"] == "299.00"


# ---------------------------------------------------------------------------------------
# PAY-07 — refund reconciliation flips status + adjusts access (Pattern 6).
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-03 reconciles refund.succeeded → refunded + adjust")
async def test_refund_recon_flips_status_and_adjusts_access(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """A re-fetched ``refund.succeeded`` flips the payment to refunded + decrements access (PAY-07).

    The ``refund.succeeded`` webhook (re-fetched, never trusting the body) sets
    ``Payment.status=refunded`` + ``refunded_at`` and adjusts the granted access — decrementing
    ``paid_spreads_balance`` for a pack (Pattern 6). Idempotent on redelivery (status guard).
    """
    from app.models import Payment

    fake = FakeYooKassa(refund_status="succeeded")
    service = _make_service(fake)
    user = await _make_user(auth_session, paid_balance=3)  # already-granted pack to claw back
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    payment = Payment(
        user_id=user.id,
        product_id=product.id,
        provider="yookassa",
        currency="RUB",
        amount=169,
        payload=f"pay-{uuid.uuid4()}",
        telegram_payment_charge_id="pay_test_000001",  # the provider payment id seam
        status=PaymentStatus.PAID,
    )
    auth_session.add(payment)
    await auth_session.flush()

    handle = _resolve(service, "handle_webhook_event", "handle_refund_succeeded")
    await handle(auth_session, REFUND_SUCCEEDED_EVENT)

    refreshed = (
        await auth_session.execute(select(Payment).where(Payment.id == payment.id))
    ).scalar_one()
    assert refreshed.status is PaymentStatus.REFUNDED
    assert refreshed.refunded_at is not None
    # Access clawed back: the 3 granted spreads are removed.
    assert await _paid_balance(auth_session, user) == 0


async def test_admin_refund_pending_does_not_claw_back(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """CR-02: an admin refund whose ЮKassa refund is NOT yet ``succeeded`` must NOT revoke access.

    ``refund_payment`` initiates the refund at ЮKassa (money-first, protecting the user) but reconciles
    — flipping REFUNDED + clawing back the granted spreads — ONLY on a confirmed ``succeeded`` refund.
    A ``pending`` refund leaves the payment PAID and the balance intact; the ``refund.succeeded``
    webhook reconciles (idempotently) when it settles. Revoking access on an unconfirmed refund would
    risk the user losing both access and money.
    """
    from app.models import Payment

    fake = FakeYooKassa(refund_status="pending")  # ЮKassa refund not yet final
    service = _make_service(fake)
    user = await _make_user(auth_session, paid_balance=3)
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    payment = Payment(
        user_id=user.id,
        product_id=product.id,
        provider="yookassa",
        currency="RUB",
        amount=169,
        payload=f"pay-{uuid.uuid4()}",
        provider_payment_id=f"pay_pending_{uuid.uuid4().hex[:8]}",
        status=PaymentStatus.PAID,
    )
    auth_session.add(payment)
    await auth_session.flush()

    await service.refund_payment(auth_session, payment)

    refreshed = (
        await auth_session.execute(select(Payment).where(Payment.id == payment.id))
    ).scalar_one()
    # Refund initiated at ЮKassa, but NOT reconciled locally until it succeeds.
    assert refreshed.status is PaymentStatus.PAID  # not flipped to REFUNDED on a pending refund
    assert await _paid_balance(auth_session, user) == 3  # access NOT clawed back yet
    assert any(c[0] == "create_refund" for c in fake.recorded_calls)  # the refund WAS initiated

"""PAY-06 — the recurring-renewal SWEEP (due selection, charge delegation, failure isolation).

Target plan: **Plan 07-06** (``core/scheduler.py`` daily sweep + ``PaymentService.find_due_subscriptions``).
Unlike the Wave-0 red stubs these are NOT xfail — Plan 03 (renewal charge) and Plan 06 (sweep +
query) both exist, so the assertions run green (or clean-skip without Postgres, via ``auth_session``
→ ``_db_ready``). Every charge goes through ``FakeYooKassa`` (the only ЮKassa surface in the suite —
threat T-07-TEST-LIVE); nothing reaches the live host. DB-touching tests run inside the
transaction-isolated ``auth_session`` (inner ``commit()`` becomes a savepoint release, rolled back at
teardown) so the renewal rows the charge writes never persist between tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, Subscription, User, UserLimits
from app.models.enums import ProductType, SubscriptionStatus
from tests.integration.conftest import FakeYooKassa

_SAVED_METHOD = "pm_test_saved_0001"


# ---------------------------------------------------------------------------------------
# Helpers — real user / subscription-product / subscription rows in the isolated session.
# ---------------------------------------------------------------------------------------


async def _make_user(session: AsyncSession) -> User:
    """Insert a fresh user + its ``user_limits`` row (the buckets are irrelevant to the sweep)."""
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(UserLimits(user_id=user.id, free_weekly_limit=3, free_used_this_week=3))
    await session.flush()
    return user


async def _make_sub_product(session: AsyncSession, slug: str) -> Product:
    """Upsert an active SUBSCRIPTION product (299₽/30d). Idempotent by slug (leak/seed-safe)."""
    product = (
        await session.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if product is None:
        product = Product(slug=slug)
        session.add(product)
    product.title = f"Тест {slug}"
    product.product_type = ProductType.SUBSCRIPTION
    product.stars_price = 299
    product.spreads_amount = None
    product.subscription_days = 30
    product.is_active = True
    await session.flush()
    return product


async def _make_sub(
    session: AsyncSession,
    *,
    user: User,
    product: Product,
    status: SubscriptionStatus,
    period_end: datetime,
    period_index: int = 0,
) -> Subscription:
    """Seed a Subscription with a saved payment method (the merchant-initiated renewal seam)."""
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=user.id,
        product_id=product.id,
        payment_method_id=_SAVED_METHOD,
        status=status,
        current_period_start=now - timedelta(days=30),
        current_period_end=period_end,
        period_index=period_index,
    )
    session.add(sub)
    await session.flush()
    return sub


class _OneFailingYooKassa(FakeYooKassa):
    """A FakeYooKassa that raises on the renewal charge whose Idempotence-Key contains a marker.

    Models "one subscription's charge fails" so the sweep's per-subscription isolation can be proven:
    the failing sub ends PAYMENT_FAILED (renew_subscription swallows the charge error, D-10) while
    every other due subscription is still charged.
    """

    def __init__(self, *, fail_key_substr: str, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._fail_key_substr = fail_key_substr

    async def create_payment(self, *, idempotence_key: str, **kwargs: object) -> object:
        if self._fail_key_substr in idempotence_key:
            raise RuntimeError("simulated ЮKassa charge failure")
        return await super().create_payment(idempotence_key=idempotence_key, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# find_due_subscriptions — selects only ACTIVE + due (never CANCELED / not-yet-due).
# ---------------------------------------------------------------------------------------


async def test_find_due_selects_only_active_and_due(auth_session: AsyncSession) -> None:
    """``find_due_subscriptions`` returns only ACTIVE subs whose ``current_period_end`` has passed."""
    from app.services.payments import PaymentService

    svc = PaymentService(yookassa=FakeYooKassa())
    user = await _make_user(auth_session)
    product = await _make_sub_product(auth_session, "lunar_sweep")
    now = datetime.now(UTC)

    due = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.ACTIVE, period_end=now - timedelta(hours=1),
    )
    not_due = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.ACTIVE, period_end=now + timedelta(days=30),
    )
    canceled = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.CANCELED, period_end=now - timedelta(hours=1),
    )

    ids = {s.id for s in await svc.find_due_subscriptions(auth_session)}
    assert due.id in ids  # active + past period_end → due
    assert not_due.id not in ids  # active but window still open → not due
    assert canceled.id not in ids  # past period_end but CANCELED → never re-charged (D-10)


# ---------------------------------------------------------------------------------------
# sweep — charges each due subscription via the deterministic per-period key.
# ---------------------------------------------------------------------------------------


async def test_sweep_charges_each_due_via_fake(auth_session: AsyncSession) -> None:
    """The sweep charges a due subscription with key ``renew:<sub_id>:<next_period>`` via the fake."""
    from app.core.scheduler import sweep_due_subscriptions
    from app.services.payments import PaymentService

    fake = FakeYooKassa(succeeded=True)
    svc = PaymentService(yookassa=fake)
    user = await _make_user(auth_session)
    product = await _make_sub_product(auth_session, "lunar_sweep")
    now = datetime.now(UTC)
    sub = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.ACTIVE, period_end=now - timedelta(hours=1),
    )

    summary = await sweep_due_subscriptions(service=svc, session=auth_session)

    create_keys = [
        c[1]["idempotence_key"] for c in fake.recorded_calls if c[0] == "create_payment"
    ]
    assert f"renew:{sub.id}:1" in create_keys  # period_index 0 → next period 1 (deterministic)
    pm_calls = [
        c[1]["payment_method_id"]
        for c in fake.recorded_calls
        if c[0] == "create_payment"
    ]
    assert _SAVED_METHOD in pm_calls  # merchant-initiated (saved card), no confirmation
    assert summary["charged"] >= 1


# ---------------------------------------------------------------------------------------
# sweep — one failing charge never aborts the sweep (per-subscription isolation).
# ---------------------------------------------------------------------------------------


async def test_sweep_isolates_per_subscription_failure(auth_session: AsyncSession) -> None:
    """A failing charge on one due sub leaves it PAYMENT_FAILED but the OTHER due sub is charged."""
    from app.core.scheduler import sweep_due_subscriptions
    from app.services.payments import PaymentService

    user = await _make_user(auth_session)
    product = await _make_sub_product(auth_session, "lunar_sweep")
    now = datetime.now(UTC)
    sub_fail = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.ACTIVE, period_end=now - timedelta(hours=2),
    )
    sub_ok = await _make_sub(
        auth_session, user=user, product=product,
        status=SubscriptionStatus.ACTIVE, period_end=now - timedelta(hours=1),
    )

    fake = _OneFailingYooKassa(fail_key_substr=f"renew:{sub_fail.id}:", succeeded=True)
    svc = PaymentService(yookassa=fake)

    summary = await sweep_due_subscriptions(service=svc, session=auth_session)

    # The healthy subscription was still charged despite the other's failure.
    ok_keys = [
        c[1]["idempotence_key"] for c in fake.recorded_calls if c[0] == "create_payment"
    ]
    assert f"renew:{sub_ok.id}:1" in ok_keys
    # The failing charge → PAYMENT_FAILED, but access is kept until period end (D-10).
    assert sub_fail.status is SubscriptionStatus.PAYMENT_FAILED
    # The sweep processed both and did not propagate the failure.
    assert summary["due"] >= 2

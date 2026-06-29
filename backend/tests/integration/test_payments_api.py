"""PAY-01/02/03/04/05/07 (red stubs) — the ЮKassa payment ROUTES (products/create/webhook/refund).

Target plan: **Plan 07-04** (``api/payments.py`` — the thin router: products list, create-payment,
webhook, admin refund). Each test is the green target for one PAY-0x route behavior and
``xfail(strict=False)`` until Plan 04 lands (it **xpasses** once the route exists and behaves). The
routes do not exist yet, so today they 404 / the override symbol is missing — the future symbols
(``get_payment_service``) are imported INSIDE the test body so a missing symbol surfaces as the
xfailed assertion, never a collection-time ``ImportError``.

These run against the real HTTP stack via the ``auth_client`` fixture (in-process ASGITransport,
``get_session`` overridden to the isolated test session) and a real Bearer JWT minted through
``POST /api/auth/telegram`` (the established auth pattern from ``test_me`` / ``test_admin_guard``).
The (future) ``get_payment_service`` dependency is overridden to inject a ``FakeYooKassa``-backed
service — the only ЮKassa surface in the suite (threat T-07-TEST-LIVE); nothing reaches the live
ЮKassa host. Everything skips cleanly (via ``auth_client`` → ``_db_ready``) when Postgres is down.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.main import app
from app.models import Product
from app.models.enums import PaymentStatus, ProductType
from tests.conftest import TEST_BOT_TOKEN, make_init_data
from tests.integration.conftest import FakeYooKassa

_TG_USER = {"id": 770700001, "first_name": "Покупатель", "username": "buyer_probe"}
_ADMIN_USER = {"id": 770700111, "first_name": "Хранитель", "username": "refund_admin"}
_NORMAL_USER = {"id": 770700222, "first_name": "Гость", "username": "refund_guest"}

# A ЮKassa IP (from the published allowlist, 07-RESEARCH Code Examples) for the webhook IP gate.
YOOKASSA_IP = "185.71.76.1"
NON_YOOKASSA_IP = "203.0.113.7"  # TEST-NET-3, never a ЮKassa source

# UNSIGNED webhook envelope (D-05 — the handler must re-fetch, never trust this body).
SUCCEEDED_EVENT = {
    "type": "notification",
    "event": "payment.succeeded",
    "object": {"id": "pay_test_000001", "status": "succeeded"},
}


async def _auth(client: object, user: dict) -> str:
    """Authenticate a Telegram user and return the Bearer access token."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=user)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _make_product(
    session: AsyncSession,
    *,
    slug: str,
    product_type: ProductType = ProductType.ONE_TIME_SPREADS,
    price_rub: int = 169,
    spreads_amount: int | None = 3,
    is_active: bool = True,
) -> Product:
    """Insert a ``products`` row (the server-authoritative price source) in the test session."""
    product = Product(
        slug=slug,
        title=f"Тест {slug}",
        product_type=product_type,
        stars_price=price_rub,
        spreads_amount=spreads_amount,
        subscription_days=30 if product_type is ProductType.SUBSCRIPTION else None,
        is_active=is_active,
    )
    session.add(product)
    await session.flush()
    return product


def _override_payment_service(fake: FakeYooKassa) -> object:
    """Override the (future) ``get_payment_service`` dependency to inject the fake-backed service.

    Returns the dependency key so the caller can pop it in a ``finally``. The import is inside the
    function so a missing ``get_payment_service`` (Plan 04 not yet landed) surfaces as the xfailed
    assertion rather than a collection error. Mirrors the ``get_reading_service`` override seam.
    """
    from app.api.payments import get_payment_service
    from app.services.payments import PaymentService

    app.dependency_overrides[get_payment_service] = lambda: PaymentService(yookassa=fake)
    return get_payment_service


# ---------------------------------------------------------------------------------------
# PAY-01 — GET /api/products lists active products only.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 adds GET /api/products")
async def test_products_list(auth_client: object, auth_session: AsyncSession) -> None:
    """``GET /api/products`` returns active products only — inactive ones are hidden (PAY-01)."""
    await _make_product(auth_session, slug="pack_1", spreads_amount=1, price_rub=69)
    await _make_product(auth_session, slug="pack_3", spreads_amount=3, price_rub=169)
    await _make_product(
        auth_session, slug="legacy_pack", spreads_amount=99, is_active=False
    )
    token = await _auth(auth_client, _TG_USER)

    resp = await auth_client.get(
        "/api/products", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200, resp.text
    slugs = {p["slug"] for p in resp.json()}
    assert {"pack_1", "pack_3"} <= slugs
    assert "legacy_pack" not in slugs  # inactive products are not offered


# ---------------------------------------------------------------------------------------
# PAY-02 — POST /api/payments/create returns confirmation_url, writes CREATED, NO grant.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 adds POST /api/payments/create")
async def test_create_payment_no_grant(
    auth_client: object, auth_session: AsyncSession
) -> None:
    """``POST /api/payments/create`` → a ``confirmation_url`` + a CREATED row, NO balance change (PAY-02).

    Grant-on-create is the classic fraud hole (Pattern 2): the create path NEVER touches balances.
    The response carries the ЮKassa ``confirmation_url`` (FakeYooKassa returns one), and a CREATED
    ``payments`` row is written for the later webhook to transition.
    """
    from sqlalchemy import func, select

    from app.models import Payment, User, UserLimits

    fake = FakeYooKassa(succeeded=True)
    await _make_product(auth_session, slug="pack_3", spreads_amount=3, price_rub=169)
    token = await _auth(auth_client, _TG_USER)
    key = _override_payment_service(fake)
    try:
        resp = await auth_client.post(
            "/api/payments/create",
            json={"product_slug": "pack_3"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(key, None)

    assert resp.status_code in (200, 201), resp.text
    assert resp.json().get("confirmation_url")  # the URL the Mini App opens via openLink

    # A CREATED payments row exists; NO balance was granted on creation.
    user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    created_count = await auth_session.scalar(
        select(func.count()).select_from(Payment).where(Payment.user_id == user.id)
    )
    assert created_count == 1
    limits = (
        await auth_session.execute(
            select(UserLimits).where(UserLimits.user_id == user.id)
        )
    ).scalar_one_or_none()
    # No paid balance granted at create time (grant happens only at the confirmed webhook).
    assert limits is None or limits.paid_spreads_balance == 0


# ---------------------------------------------------------------------------------------
# PAY-03 — server recomputes price from the products row; inactive product → 4xx.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 recomputes price server-side + rejects inactive")
async def test_create_recomputes_price(
    auth_client: object, auth_session: AsyncSession
) -> None:
    """The charged amount equals the ``products`` row price; a client-sent amount is ignored (PAY-03).

    Amount/price tampering (Pitfall 4 / T-07-AMOUNT): the create endpoint accepts only a
    ``product_slug`` and recomputes ``amount`` from the row. Even if a malicious client smuggles a
    ``price``/``amount`` field, the value sent to ЮKassa is the server's. An inactive product → 4xx.
    """
    fake = FakeYooKassa(succeeded=True)
    await _make_product(auth_session, slug="pack_10", spreads_amount=10, price_rub=449)
    await _make_product(
        auth_session, slug="dead_pack", spreads_amount=3, is_active=False
    )
    token = await _auth(auth_client, _TG_USER)
    key = _override_payment_service(fake)
    try:
        # A tampered client amount (1₽) must be ignored — the server recomputes 449.00.
        resp = await auth_client.post(
            "/api/payments/create",
            json={"product_slug": "pack_10", "price": 1, "amount": "1.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (200, 201), resp.text
        create_calls = [c for c in fake.recorded_calls if c[0] == "create_payment"]
        assert create_calls, "create must call ЮKassa with the server-computed amount"
        assert create_calls[-1][1]["value_rub"] == "449.00"  # the products row, not the client

        # An inactive product cannot be purchased → 4xx (no ЮKassa call for it).
        resp_inactive = await auth_client.post(
            "/api/payments/create",
            json={"product_slug": "dead_pack"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert 400 <= resp_inactive.status_code < 500
    finally:
        app.dependency_overrides.pop(key, None)


# ---------------------------------------------------------------------------------------
# PAY-04 — webhook grants on the re-fetched succeeded status.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 webhook re-fetches + grants on succeeded")
async def test_webhook_grants_on_refetched_succeeded(
    auth_client: object, auth_session: AsyncSession
) -> None:
    """Posting the webhook envelope from a ЮKassa IP re-fetches the payment and grants (PAY-04).

    The webhook handler takes ``object.id``, IGNORES ``object.status`` (unsigned body), re-fetches
    via ЮKassa (FakeYooKassa → ``succeeded``) and grants the pack's spreads inside one transaction.
    A CREATED payments row for that provider id is seeded so the grant has a row to transition.
    """
    from sqlalchemy import select

    from app.models import Payment, User, UserLimits

    fake = FakeYooKassa(succeeded=True)
    await _auth(auth_client, _TG_USER)  # mint the user via auth (the webhook needs no Bearer)
    user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    auth_session.add(
        UserLimits(user_id=user.id, free_weekly_limit=3, free_used_this_week=3)
    )
    auth_session.add(
        Payment(
            user_id=user.id,
            product_id=product.id,
            provider="yookassa",
            currency="RUB",
            amount=169,
            payload=f"pay-{uuid.uuid4()}",
            telegram_payment_charge_id="pay_test_000001",
            status=PaymentStatus.CREATED,
        )
    )
    await auth_session.flush()

    key = _override_payment_service(fake)
    try:
        resp = await auth_client.post(
            "/api/payments/yookassa/webhook",
            json=SUCCEEDED_EVENT,
            headers={"X-Forwarded-For": YOOKASSA_IP},
        )
    finally:
        app.dependency_overrides.pop(key, None)

    assert resp.status_code == 200, resp.text  # always 200 on a handled event
    limits = (
        await auth_session.execute(
            select(UserLimits).where(UserLimits.user_id == user.id)
        )
    ).scalar_one()
    assert limits.paid_spreads_balance == product.spreads_amount
    assert any(c[0] == "find_payment" for c in fake.recorded_calls)  # re-fetched (D-05)


# ---------------------------------------------------------------------------------------
# PAY-05 — webhook idempotent + IP-gated; body status never trusted.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 webhook is idempotent + IP-gated")
async def test_webhook_idempotent_and_ip_gated(
    auth_client: object, auth_session: AsyncSession
) -> None:
    """Same event twice grants once; a non-ЮKassa source IP is rejected; body status untrusted (PAY-05).

    Two invariants in one route test:
      * **IP gate** — a POST from a non-ЮKassa IP is rejected/ignored (no grant), even with a valid
        body (ЮKassa does not sign webhooks → IP allowlist + re-fetch is the only defense);
      * **idempotency** — two identical deliveries from a ЮKassa IP grant exactly once (Pitfall 2).
    """
    from sqlalchemy import select

    from app.models import Payment, User, UserLimits

    fake = FakeYooKassa(succeeded=True)
    await _auth(auth_client, _TG_USER)  # mint the user via auth (token unused here)
    user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    auth_session.add(
        UserLimits(user_id=user.id, free_weekly_limit=3, free_used_this_week=3)
    )
    auth_session.add(
        Payment(
            user_id=user.id,
            product_id=product.id,
            provider="yookassa",
            currency="RUB",
            amount=169,
            payload=f"pay-{uuid.uuid4()}",
            telegram_payment_charge_id="pay_test_000001",
            status=PaymentStatus.CREATED,
        )
    )
    await auth_session.flush()

    key = _override_payment_service(fake)
    try:
        # (1) Non-ЮKassa source IP → rejected/ignored, NO grant.
        resp_bad_ip = await auth_client.post(
            "/api/payments/yookassa/webhook",
            json=SUCCEEDED_EVENT,
            headers={"X-Forwarded-For": NON_YOOKASSA_IP},
        )
        assert resp_bad_ip.status_code in (200, 403)  # ignored or rejected, never a grant
        limits = (
            await auth_session.execute(
                select(UserLimits).where(UserLimits.user_id == user.id)
            )
        ).scalar_one()
        assert limits.paid_spreads_balance == 0  # the forged-IP delivery granted nothing

        # (2) Two identical deliveries from a real ЮKassa IP → grant exactly once.
        await auth_client.post(
            "/api/payments/yookassa/webhook",
            json=SUCCEEDED_EVENT,
            headers={"X-Forwarded-For": YOOKASSA_IP},
        )
        await auth_session.refresh(limits)
        once = limits.paid_spreads_balance
        await auth_client.post(
            "/api/payments/yookassa/webhook",
            json=SUCCEEDED_EVENT,
            headers={"X-Forwarded-For": YOOKASSA_IP},
        )
        await auth_session.refresh(limits)
        assert once == product.spreads_amount
        assert limits.paid_spreads_balance == once  # NOT doubled on redelivery
    finally:
        app.dependency_overrides.pop(key, None)


# ---------------------------------------------------------------------------------------
# PAY-07 / T-07-IDOR — refund requires admin.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Plan 07-04 gates the refund route behind require_admin")
async def test_refund_requires_admin(
    auth_client: object, auth_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``POST /api/payments/{id}/refund`` is 403 for a non-admin JWT, allowed for an admin (PAY-07).

    The refund endpoint is admin-only for MVP (D-14 / T-07-IDOR): a normal user's Bearer → 403,
    an allowlisted admin's Bearer reaches the handler. The allowlist is monkeypatched so the test
    does not depend on ambient env config (mirrors ``test_admin_guard``).
    """
    from sqlalchemy import select

    from app.models import Payment, User

    monkeypatch.setattr(settings, "ADMIN_TELEGRAM_IDS", [_ADMIN_USER["id"]])
    fake = FakeYooKassa(refund_status="succeeded")

    # Seed a PAID payment to refund (owned by the buyer; admin acts on it).
    admin_token = await _auth(auth_client, _ADMIN_USER)
    buyer_token = await _auth(auth_client, _NORMAL_USER)
    buyer = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _NORMAL_USER["id"])
        )
    ).scalar_one()
    product = await _make_product(auth_session, slug="pack_3", spreads_amount=3)
    payment = Payment(
        user_id=buyer.id,
        product_id=product.id,
        provider="yookassa",
        currency="RUB",
        amount=169,
        payload=f"pay-{uuid.uuid4()}",
        telegram_payment_charge_id="pay_test_000001",
        status=PaymentStatus.PAID,
    )
    auth_session.add(payment)
    await auth_session.flush()

    key = _override_payment_service(fake)
    try:
        # Non-admin → 403.
        resp_forbidden = await auth_client.post(
            f"/api/payments/{payment.id}/refund",
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
        assert resp_forbidden.status_code == 403

        # Admin → reaches the handler (200/202, not a 403).
        resp_admin = await auth_client.post(
            f"/api/payments/{payment.id}/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_admin.status_code in (200, 202)
    finally:
        app.dependency_overrides.pop(key, None)

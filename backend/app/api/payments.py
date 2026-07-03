"""ЮKassa money-path HTTP surface (PAY-01/02/03/04/05/07) — the thin router.

Mirrors ``readings.py``: authenticate (or IP-gate the webhook), validate the body, resolve the
product / subscription, and delegate ALL money logic to ``PaymentService`` (Plan 03). No business
logic lives here — routes only authenticate, validate, IP-gate, and map errors.

Security disciplines wired at the edge:
  * every CLIENT route is behind ``get_current_user`` (identity = the JWT ``sub`` only, never a body
    field — T-07-IDOR); the refund is additionally behind ``require_admin`` (privileged, T-07-IDOR).
  * ``POST /payments/create`` carries only a ``product_slug`` — the price is recomputed in the
    service from the ``products`` row (T-07-AMOUNT); create NEVER grants (Pattern 2).
  * the ЮKassa webhook is UNSIGNED: it is IP-allowlist-gated HERE (a cheap reject before the
    re-fetch / grant work, T-07-WEBHOOK-FORGE / T-07-WEBHOOK-DOS) and the service re-fetches by id
    before granting (D-05). It ALWAYS returns 200 on a handled / duplicate event so ЮKassa stops
    redelivering (T-07-REPLAY); only a genuine processing failure returns 5xx (so ЮKassa retries).

The ``get_payment_service`` dependency is the test seam: overridden via ``app.dependency_overrides``
to inject a ``FakeYooKassa``-backed service so the money-path runs with zero network and zero real
money moving (threat T-07-TEST-LIVE) — the direct analog of ``get_reading_service``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_admin
from app.models import Payment, Product, Subscription
from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.user import User
from app.schemas.payment import (
    CreatePaymentIn,
    CreatePaymentOut,
    ProductOut,
    RefundIn,
    WebhookEnvelope,
)
from app.services.payments import PaymentService, is_from_yookassa

logger = logging.getLogger("app.payments")

router = APIRouter(tags=["payments"])


def get_payment_service() -> PaymentService:
    """Provide the default ``PaymentService`` (the real ЮKassa client).

    Overridden in tests via ``app.dependency_overrides[get_payment_service]`` to inject a service
    built with ``FakeYooKassa`` so the money-path is exercised without a live ЮKassa call — the
    direct analog of ``get_reading_service`` for ``ReadingService``.
    """
    return PaymentService()


# --------------------------------------------------------------------------- catalog (PAY-01)


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Product]:
    """List the active purchasable products — the shop catalog (PAY-01).

    Behind ``get_current_user`` (the shop is an authenticated surface). Returns only ``is_active``
    rows: a retired pack is hidden, never offered. ``ProductOut`` maps ``stars_price`` (integer
    RUBLES, A1) → ``price_rub`` and never serializes any secret/amount internals (T-07-SECRET-LEAK).
    """
    rows = (
        (await session.execute(select(Product).where(Product.is_active.is_(True))))
        .scalars()
        .all()
    )
    return list(rows)


# --------------------------------------------------------------------------- create (PAY-02/03)


@router.post("/payments/create", response_model=CreatePaymentOut)
async def create_payment(
    body: CreatePaymentIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    service: PaymentService = Depends(get_payment_service),
) -> CreatePaymentOut:
    """Create a ЮKassa payment and return its ``confirmation_url`` — grants NOTHING (PAY-02/03).

    Resolves the product by ``product_slug`` (active only → a clean 404 otherwise, no internal
    leak). The user is the JWT ``sub`` only (T-07-IDOR — no body identity); the body carries no
    amount (T-07-AMOUNT — the schema has none, and the service recomputes the price from the
    ``products`` row). Delegates to ``PaymentService.create_payment`` (writes a CREATED row + calls
    ЮKassa; NO grant, Pattern 2) and returns the hosted ``confirmation_url`` + ids for polling/audit.
    """
    product = (
        await session.execute(
            select(Product).where(
                Product.slug == body.product_slug,
                Product.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")

    payment = await service.create_payment(session, user, product)
    return CreatePaymentOut(
        confirmation_url=payment.confirmation_url or "",
        payment_id=str(payment.id),
        provider_payment_id=payment.provider_payment_id or "",
    )


# --------------------------------------------------------------------------- webhook (PAY-04/05)


def _client_ip(request: Request) -> str:
    """Best-effort client IP: the left-most ``X-Forwarded-For`` (timeweb proxy) else the socket peer.

    The webhook runs behind the timeweb reverse proxy, so the real ЮKassa source is the left-most
    ``X-Forwarded-For`` entry; ``request.client.host`` is the fallback for a direct hit. A spoofed
    XFF only matters to an attacker already inside the published ЮKassa ranges — the re-fetch-by-id
    (D-05) remains the authoritative guard regardless (this allowlist is defence-in-depth).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/payments/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    envelope: WebhookEnvelope,
    session: AsyncSession = Depends(get_session),
    service: PaymentService = Depends(get_payment_service),
) -> Response:
    """ЮKassa notification sink (UNSIGNED) — IP-gated + re-fetch-before-grant (PAY-04/05).

    ЮKassa does not sign webhooks, so authenticity rests on two controls: this IP allowlist (a
    cheap reject of any non-ЮKassa source BEFORE the re-fetch / grant work — T-07-WEBHOOK-FORGE /
    T-07-WEBHOOK-DOS) and the service's re-fetch-by-id (D-05 — the body ``status`` is NEVER trusted
    for a grant; the handler passes the envelope on to the body-status-blind service dispatcher).
    ALWAYS returns 200 on a handled OR duplicate event so ЮKassa stops redelivering (T-07-REPLAY);
    only a genuine processing failure returns 500 so ЮKassa retries.
    """
    ip = _client_ip(request)
    if not is_from_yookassa(ip):
        # Cheap reject before any re-fetch / DB grant work (defence-in-depth; re-fetch is the guard).
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        await service.handle_webhook_event(session, envelope.model_dump())
    except Exception:  # noqa: BLE001 - a genuine processing failure → 500 so ЮKassa retries.
        logger.exception(
            "yookassa_webhook_failed", extra={"event": "payment.webhook_error"}
        )
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # Handled OR duplicate (the service's grant is an idempotent no-op on redelivery) → 200 so
    # ЮKassa stops redelivering (T-07-REPLAY).
    return Response(status_code=status.HTTP_200_OK)


# --------------------------------------------------------------------------- refund (PAY-07, admin)


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: uuid.UUID,
    body: RefundIn | None = None,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    service: PaymentService = Depends(get_payment_service),
) -> dict[str, str]:
    """Admin-only refund of a payment (PAY-07, T-07-IDOR) — claws back the GRANTED entitlement.

    ``require_admin`` gates the route (a non-admin JWT → 403). The payment is loaded by the typed
    UUID path (malformed → 422; missing → 404). Delegates to ``PaymentService.refund_payment``,
    which refunds at ЮKassa then decrements the granted units (NEVER the RUB amount —
    T-07-REFUND-OVERCREDIT), idempotently. The body is optional (``None`` ⇒ full refund).
    """
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "payment not found")

    amount_rub = body.amount_rub if body else None
    await service.refund_payment(session, payment, amount_rub=amount_rub)
    return {"payment_id": str(payment.id), "status": PaymentStatus.REFUNDED.value}


# --------------------------------------------------------------------------- cancel (self-serve, D-10)


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Self-serve subscription cancel (D-10) — KEEPS access until the current period end.

    JWT-scoped: the subscription is loaded scoped to ``user.id`` so a non-owned id is a clean 404
    (no existence leak, T-07-IDOR — mirrors ``reading.py``). Flips ``status=CANCELED`` + stamps
    ``canceled_at`` but does NOT touch ``current_period_end`` — the subscriber keeps the window they
    already paid for, and the renewal sweep simply won't recharge a CANCELED row.
    """
    sub = (
        await session.execute(
            select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "subscription not found")

    sub.status = SubscriptionStatus.CANCELED
    sub.canceled_at = datetime.now(UTC)
    await session.commit()
    return {
        "id": str(sub.id),
        "status": SubscriptionStatus.CANCELED.value,
        "current_period_end": (
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
    }


__all__ = ["router", "get_payment_service"]

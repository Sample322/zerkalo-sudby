"""``PaymentService`` dependency seam for the ЮKassa money-path routes.

This module currently exposes ONLY the ``get_payment_service`` FastAPI dependency — the mirror of
``readings.py``'s ``get_reading_service`` (a zero-arg provider returning the default service with
its real collaborator wired). It is the injection point Plan 01's tests + integration conftest
reference::

    app.dependency_overrides[get_payment_service] = lambda: PaymentService(yookassa=fake)

so the create / webhook / refund flows run end-to-end against ``FakeYooKassa`` with zero network
and zero real money moving (threat T-07-TEST-LIVE) — exactly the ``ReadingService(safety=...,
llm=...)`` seam ``get_reading_service`` provides.

The routes themselves (``GET /api/products``, create-payment, the IP-gated webhook, admin refund)
are added by Plan 07-05 onto this same module and ``router``; this plan (07-04) fills the
SUBSCRIPTION/PAID consume-gate seams in ``reading.py`` and only needs the dependency to exist so
that gate's spendable grant is reachable through the established override seam.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.payments import PaymentService

router = APIRouter(tags=["payments"])


def get_payment_service() -> PaymentService:
    """Provide the default ``PaymentService`` (the real ЮKassa client).

    Overridden in tests via ``app.dependency_overrides[get_payment_service]`` to inject a service
    built with ``FakeYooKassa`` so the money-path is exercised without a live ЮKassa call — the
    direct analog of ``get_reading_service`` for ``ReadingService``.
    """
    return PaymentService()


__all__ = ["router", "get_payment_service"]

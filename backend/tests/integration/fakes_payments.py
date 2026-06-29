"""``FakeYooKassa`` — the no-real-charge ЮKassa stand-in (Phase-7 Wave-0 substrate).

This is the **only** ЮKassa surface the test suite ever touches: the test harness → ЮKassa
trust boundary is severed here (threat T-07-TEST-LIVE). No test reaches the live ЮKassa host,
and this module **NEVER imports the real ЮKassa SDK package** — a grep gate over ``backend/tests``
(for the live-host string and for an import of that package) asserts that invariant in CI and in
the plan's acceptance criteria. Those two forbidden literals are deliberately kept out of this
docstring so the gate stays green.

It mirrors the established ``FakeLLM`` / ``FakeSafety`` seam (``tests/integration/conftest.py``):
an injectable, controllable, call-recording stand-in that a later plan substitutes for the real
ЮKassa client. Plans 03/04 wire it into ``services/payments.py`` via the service constructor +
``app.dependency_overrides[get_payment_service]`` (the same pattern ``ReadingService`` uses for
``FakeSafety``/``FakeLLM`` via ``get_reading_service``), so the create/webhook/refund paths are
exercised end-to-end with zero network and zero real money moving.

The four methods mirror the ЮKassa v3 operations the service seam (RESEARCH "Component
Responsibilities" / Pattern 1) will call — wrapped in the real code via
``anyio.to_thread.run_sync`` around the sync SDK, but here plain ``async def`` so the seam is
awaitable either way:

  * ``create_payment(*, value_rub, return_url, idempotence_key, metadata, save_payment_method)``
    → a ``pending`` payment object carrying ``confirmation.confirmation_url`` (PAY-02);
  * ``find_payment(payment_id)`` → the re-fetched payment object whose ``status`` the webhook
    handler trusts (the D-05 "re-fetch, never trust the body" discipline — PAY-04/05);
  * ``create_refund(*, payment_id, value_rub, idempotence_key)`` → a refund object (PAY-07);
  * ``find_refund(refund_id)`` → the re-fetched refund object.

Controllable behavior (so a test can drive every branch):
  * ``succeeded`` — the status ``find_payment`` reports on re-fetch (``"succeeded"`` vs
    ``"pending"``/``"canceled"`` lets a test assert "grant only on re-fetched succeeded");
  * ``next_status`` — explicit override for the re-fetched payment status (wins over ``succeeded``);
  * ``payment_method_id`` — the saved-method id returned when ``save_payment_method=True`` (PAY-06);
  * ``refund_status`` — the status ``find_refund`` / ``create_refund`` reports;
  * ``recorded_calls`` — an ordered list of ``(method, kwargs)`` tuples so a test asserts the
    deterministic recurring Idempotence-Key (``renew:<sub_id>:<period_index>``, Pitfall 5) and the
    server-recomputed amount (``value_rub`` from the ``products`` row, never the client — Pitfall 4).

Returned objects are ``SimpleNamespace`` instances exposing the exact ЮKassa fields the service
reads (``id``, ``status``, ``amount={"value","currency"}``, ``confirmation={"confirmation_url"}``,
``payment_method={"id","saved"}``, ``metadata``) plus a ``json()`` accessor returning the same data
as a plain ``dict`` for the ``payments.raw_update`` JSONB audit column — matching how the real SDK
objects expose ``.json()``.
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace
from typing import Any

# ЮKassa v3 status literals the service branches on (RESEARCH "lifecycle" + Code Examples).
STATUS_PENDING = "pending"
STATUS_SUCCEEDED = "succeeded"
STATUS_CANCELED = "canceled"
CURRENCY_RUB = "RUB"


class FakeYooKassa:
    """Injectable, controllable stand-in for the ЮKassa v3 client — never hits the network.

    Construct with the behavior a test needs, inject it into the (future) payment service via the
    constructor seam (Plan 03/04 + ``app.dependency_overrides``), drive the flow, then assert
    against ``recorded_calls`` and the returned objects. See the module docstring for the full
    contract. This class deliberately has NO dependency on the real ``yookassa`` package.
    """

    def __init__(
        self,
        *,
        succeeded: bool = True,
        next_status: str | None = None,
        payment_method_id: str = "pm_test_saved_0001",
        refund_status: str = STATUS_SUCCEEDED,
    ) -> None:
        # The status ``find_payment`` reports on re-fetch. ``next_status`` (if given) wins so a test
        # can force ``pending``/``canceled`` explicitly; otherwise ``succeeded`` maps to the literal.
        self._refetch_status = next_status or (
            STATUS_SUCCEEDED if succeeded else STATUS_PENDING
        )
        self._payment_method_id = payment_method_id
        self._refund_status = refund_status
        # Ordered audit of every call: list[tuple[str, dict[str, Any]]]. Tests assert the
        # deterministic recurring key + the server-recomputed amount from this.
        self.recorded_calls: list[tuple[str, dict[str, Any]]] = []
        # Monotonic id generators so successive creates get distinct, inspectable ids.
        self._payment_ids = (f"pay_test_{n:06d}" for n in itertools.count(1))
        self._refund_ids = (f"ref_test_{n:06d}" for n in itertools.count(1))
        # Remember created payments by id so ``find_payment`` can echo amount/metadata back.
        self._created: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ create / find payment

    async def create_payment(
        self,
        *,
        value_rub: str,
        return_url: str,
        idempotence_key: str,
        metadata: dict[str, Any],
        save_payment_method: bool = False,
        payment_method_id: str | None = None,
    ) -> SimpleNamespace:
        """Create a (faked) ЮKassa payment → a ``pending`` object with a ``confirmation_url``.

        Records the call (so a test can assert the server-recomputed ``value_rub`` and the
        Idempotence-Key). When ``save_payment_method`` is set the returned object carries a
        ``payment_method`` block (the saved-card id the subscription stores, PAY-06). A
        ``payment_method_id`` argument (no ``confirmation`` in real usage) models a
        merchant-initiated renewal charge — the recurring path (Pitfall 5).
        """
        self.recorded_calls.append(
            (
                "create_payment",
                {
                    "value_rub": value_rub,
                    "return_url": return_url,
                    "idempotence_key": idempotence_key,
                    "metadata": dict(metadata),
                    "save_payment_method": save_payment_method,
                    "payment_method_id": payment_method_id,
                },
            )
        )
        pid = next(self._payment_ids)
        self._created[pid] = {"value_rub": value_rub, "metadata": dict(metadata)}
        # A renewal (payment_method_id given, no confirmation) is created already-succeeding so the
        # sweep's grant path can re-fetch a ``succeeded`` object; an interactive create stays pending
        # until the user pays (the webhook later re-fetches the final status).
        is_renewal = payment_method_id is not None
        status = STATUS_SUCCEEDED if is_renewal else STATUS_PENDING
        payment_method = (
            {"id": payment_method_id or self._payment_method_id, "saved": True}
            if (save_payment_method or is_renewal)
            else None
        )
        return self._payment_object(
            pid,
            status=status,
            value_rub=value_rub,
            metadata=metadata,
            confirmation_url=(
                None if is_renewal else f"https://yoomoney.test/checkout/{pid}"
            ),
            payment_method=payment_method,
        )

    async def find_payment(self, payment_id: str) -> SimpleNamespace:
        """Re-fetch a payment by id (the D-05 authoritative check) → the configured status.

        This is the call the webhook handler MUST make before granting: it ignores the unsigned
        webhook body and trusts only this re-fetched ``status``. The status comes from the
        ``succeeded``/``next_status`` construction args, so a test toggles grant-vs-no-grant here.
        Echoes back the amount/metadata of a previously-created payment when known.
        """
        self.recorded_calls.append(("find_payment", {"payment_id": payment_id}))
        created = self._created.get(payment_id, {})
        return self._payment_object(
            payment_id,
            status=self._refetch_status,
            value_rub=created.get("value_rub", "0.00"),
            metadata=created.get("metadata", {}),
            payment_method={"id": self._payment_method_id, "saved": True},
        )

    # ------------------------------------------------------------------ create / find refund

    async def create_refund(
        self, *, payment_id: str, value_rub: str, idempotence_key: str
    ) -> SimpleNamespace:
        """Create a (faked) refund for a payment (PAY-07) → a refund object with the set status."""
        self.recorded_calls.append(
            (
                "create_refund",
                {
                    "payment_id": payment_id,
                    "value_rub": value_rub,
                    "idempotence_key": idempotence_key,
                },
            )
        )
        rid = next(self._refund_ids)
        return self._refund_object(
            rid, payment_id=payment_id, status=self._refund_status, value_rub=value_rub
        )

    async def find_refund(self, refund_id: str) -> SimpleNamespace:
        """Re-fetch a refund by id (the refund-reconciliation re-fetch, Pattern 6)."""
        self.recorded_calls.append(("find_refund", {"refund_id": refund_id}))
        return self._refund_object(
            refund_id, payment_id=None, status=self._refund_status, value_rub="0.00"
        )

    # ------------------------------------------------------------------ object builders

    @staticmethod
    def _payment_object(
        payment_id: str,
        *,
        status: str,
        value_rub: str,
        metadata: dict[str, Any],
        confirmation_url: str | None = None,
        payment_method: dict[str, Any] | None = None,
    ) -> SimpleNamespace:
        """Build a ЮKassa-shaped payment object (the fields the service reads) + a ``json()`` accessor."""
        data: dict[str, Any] = {
            "id": payment_id,
            "status": status,
            "amount": {"value": value_rub, "currency": CURRENCY_RUB},
            "metadata": dict(metadata),
        }
        if confirmation_url is not None:
            data["confirmation"] = {
                "type": "redirect",
                "confirmation_url": confirmation_url,
            }
        if payment_method is not None:
            data["payment_method"] = dict(payment_method)
        return _as_object(data)

    @staticmethod
    def _refund_object(
        refund_id: str,
        *,
        payment_id: str | None,
        status: str,
        value_rub: str,
    ) -> SimpleNamespace:
        """Build a ЮKassa-shaped refund object (the fields the service reads) + a ``json()`` accessor."""
        data: dict[str, Any] = {
            "id": refund_id,
            "status": status,
            "amount": {"value": value_rub, "currency": CURRENCY_RUB},
            "payment_id": payment_id,
        }
        return _as_object(data)


def _as_object(data: dict[str, Any]) -> SimpleNamespace:
    """Wrap a dict as a ЮKassa-like object: attribute access + a ``json()`` returning the dict.

    The real SDK objects expose their fields as attributes and a ``.json()`` dict; the service
    persists ``payment.json()`` into ``payments.raw_update`` (JSONB audit). A ``SimpleNamespace``
    gives attribute access for free; ``json`` is bound to return a shallow copy of the source dict
    so a caller never mutates the object's backing store.
    """
    namespace = SimpleNamespace(**data)
    namespace.json = lambda: dict(data)  # type: ignore[attr-defined]
    return namespace


__all__ = [
    "CURRENCY_RUB",
    "STATUS_CANCELED",
    "STATUS_PENDING",
    "STATUS_SUCCEEDED",
    "FakeYooKassa",
]

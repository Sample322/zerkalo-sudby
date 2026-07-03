"""ЮKassa payment contracts (Phase 7, PAY-01..07) — the interface-first surface the service
(Plan 03) + routes (Plan 04) + shop FE (Plan 08) consume.

Provider pivot (D-01): these schemas model the **ЮKassa v3** flow (RUB), NOT Telegram Stars.

Five families:
1. ``ProductOut`` — the catalog projection for ``GET /api/products`` (PAY-01). ``price_rub`` is
   sourced from ``products.stars_price`` (A1: integer RUBLES) — the column keeps its name, the
   API speaks ``price_rub``.
2. ``CreatePaymentIn`` — the ``POST /api/payments/create`` body. Carries **only**
   ``product_slug`` — there is deliberately NO ``amount``/``price`` field (T-07-AMOUNT): the
   server recomputes the price from the ``products`` row, so a client can never under-pay.
3. ``CreatePaymentOut`` — the create response: the ЮKassa-hosted ``confirmation_url`` the FE
   opens via ``openLink`` + the ids for polling/audit.
4. ``RefundIn`` — the admin refund body (PAY-07); ``amount_rub`` omitted ⇒ full refund.
5. ``WebhookEnvelope`` — the (UNSIGNED) ЮKassa notification body. The handler reads only
   ``object["id"]`` and re-fetches by id — it NEVER trusts ``object["status"]`` from the body
   (T-07-WEBHOOK-FORGE / Pattern 3).

``from_attributes=True`` is set where a schema maps an ORM row (``ProductOut``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    """Catalog projection for ``GET /api/products`` (PAY-01).

    Mapped from a ``Product`` ORM row, except ``price_rub`` which is read from the ORM's
    ``stars_price`` column (A1: it now holds an **integer in RUBLES**). The secret key / amount
    logic never crosses this boundary (T-07-SECRET-LEAK).
    """

    model_config = ConfigDict(from_attributes=True)

    slug: str = Field(description="стабильный идентификатор товара (pack_1 / sub_moon …)")
    title: str = Field(description="название товара для витрины")
    description: str | None = Field(
        default=None, description="краткое описание товара для витрины"
    )
    product_type: str = Field(
        description="тип товара: one_time_spreads | subscription"
    )
    price_rub: int = Field(
        validation_alias="stars_price",
        description="цена в рублях (целое; ЮKassa получает '{:.2f}' от сервиса)",
    )
    spreads_amount: int | None = Field(
        default=None,
        description="сколько раскладов даёт пакет (None для подписки)",
    )
    subscription_days: int | None = Field(
        default=None,
        description="длительность подписки в днях (None для разовых пакетов)",
    )


class CreatePaymentIn(BaseModel):
    """``POST /api/payments/create`` request body (PAY-02/03).

    Carries ONLY ``product_slug``. There is intentionally NO ``amount`` / ``price`` field —
    the server recomputes the charge amount from the ``products`` row every time
    (threat **T-07-AMOUNT**: a client-supplied amount could be tampered to pay 1₽ for the
    10-pack). Mirrors ``reading.py``'s server-authoritative posture.

    ``extra="ignore"`` (not ``forbid``): a malicious client may smuggle a ``price`` / ``amount``
    field, and it is harmlessly DROPPED here — the charged value is always recomputed from the
    ``products`` row in the service, so the smuggled amount is inert (asserted by
    ``test_create_recomputes_price``, which posts a tampered amount and verifies the server-side
    ``value_rub`` wins). Ignoring rather than 422-rejecting keeps the create call robust to future
    additive client fields while the server-authoritative price closes T-07-AMOUNT.
    """

    model_config = ConfigDict(extra="ignore")

    product_slug: str = Field(
        min_length=1,
        description="slug покупаемого товара; цена пересчитывается на сервере (T-07-AMOUNT)",
    )


class CreatePaymentOut(BaseModel):
    """``POST /api/payments/create`` response (PAY-02).

    The FE opens ``confirmation_url`` via ``openLink`` and then polls ``GET /api/me`` until the
    webhook grants access (D-07 — the create call NEVER grants, Pattern 2). ``payment_id`` is
    OUR ``payments.id`` (for client-side correlation); ``provider_payment_id`` is the ЮKassa id.
    """

    confirmation_url: str = Field(description="ЮKassa-страница оплаты (открывается через openLink)")
    payment_id: str = Field(description="наш payments.id (UUID) созданной CREATED-записи")
    provider_payment_id: str = Field(description="id платежа в ЮKassa")


class RefundIn(BaseModel):
    """``POST /api/payments/{id}/refund`` request body (PAY-07, admin-only).

    ``amount_rub`` omitted ⇒ a **full** refund of the original payment; a value ⇒ partial
    (min 1₽, enforced by ЮKassa). The route is ``require_admin`` (T-07-IDOR); the schema carries
    no payment/user id — the target payment comes from the path, scoped server-side.
    """

    model_config = ConfigDict(extra="forbid")

    amount_rub: int | None = Field(
        default=None,
        ge=1,
        description="сумма возврата в рублях; None → полный возврат исходного платежа",
    )


class WebhookEnvelope(BaseModel):
    """The ЮKassa notification body POSTed to the webhook (PAY-04/05).

    ЮKassa does NOT sign webhooks, so this body is **untrusted**: the handler takes only
    ``object["id"]`` and re-fetches the object from the API, granting strictly on the
    **re-fetched** ``succeeded`` status — it NEVER trusts ``object["status"]`` from here
    (threat T-07-WEBHOOK-FORGE / Pattern 3). ``extra`` is allowed because ЮKassa may add fields.
    """

    type: str = Field(description="всегда 'notification'")
    event: str = Field(
        description="payment.succeeded | payment.canceled | refund.succeeded …"
    )
    object: dict = Field(
        description="объект уведомления; читаем ТОЛЬКО object['id'], статус перепроверяем по API",
    )


__all__ = [
    "ProductOut",
    "CreatePaymentIn",
    "CreatePaymentOut",
    "RefundIn",
    "WebhookEnvelope",
]

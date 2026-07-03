// ЮKassa shop API (PAY-01/08). fetchProducts + createPayment + cancelSubscription over the Bearer
// `apiFetch` seam (mirrors api/me.ts's MeError pattern — one source of truth for the shape, no
// `any`). SECURITY posture: the client sends ONLY a `product_slug` on create (T-07-AMOUNT — the
// server recomputes the price from the products row); it NEVER self-grants — the granted balance /
// subscription is read back from GET /api/me after the webhook confirms (D-07, T-07-CLIENT-GRANT).

import { apiFetch } from "./client";

/** A purchasable product (mirrors backend `ProductOut`; `price_rub` is a whole-ruble integer). */
export interface ProductOut {
  slug: string;
  title: string;
  description: string | null;
  /** "one_time_spreads" | "subscription" — narrowed at the call sites. */
  product_type: string;
  price_rub: number;
  spreads_amount: number | null;
  subscription_days: number | null;
}

/** The create-payment response (mirrors backend `CreatePaymentOut`). */
export interface CreatePaymentOut {
  confirmation_url: string;
  payment_id: string;
  provider_payment_id: string;
}

/** Thrown when a payments request returns a non-2xx status (mirrors MeError / AuthError). */
export class PaymentError extends Error {
  readonly status: number;

  constructor(status: number, message = "payment request failed") {
    super(message);
    this.name = "PaymentError";
    this.status = status;
  }
}

/** GET /api/products — the active shop catalog (server-authoritative prices, PAY-01). */
export async function fetchProducts(): Promise<ProductOut[]> {
  const res = await apiFetch("/api/products");
  if (!res.ok) throw new PaymentError(res.status);
  return (await res.json()) as ProductOut[];
}

/**
 * POST /api/payments/create — create a ЮKassa payment; returns the hosted `confirmation_url` the
 * caller opens via Telegram `openLink`. The body carries ONLY the slug — NO amount/price field
 * (T-07-AMOUNT; the server recomputes the charge). Grants nothing (D-07 — the webhook does).
 */
export async function createPayment(
  productSlug: string,
): Promise<CreatePaymentOut> {
  const res = await apiFetch("/api/payments/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_slug: productSlug }),
  });
  if (!res.ok) throw new PaymentError(res.status);
  return (await res.json()) as CreatePaymentOut;
}

/**
 * POST /api/subscriptions/{id}/cancel — self-serve cancel (D-10). Access is KEPT until the current
 * period end (the server flips status to CANCELED + stamps canceled_at, never touching
 * current_period_end). The id comes from `GET /api/me` (`limits.subscription_id`).
 */
export async function cancelSubscription(subscriptionId: string): Promise<void> {
  const res = await apiFetch(
    `/api/subscriptions/${subscriptionId}/cancel`,
    { method: "POST" },
  );
  if (!res.ok) throw new PaymentError(res.status);
}

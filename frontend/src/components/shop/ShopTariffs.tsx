// ShopTariffs — the reusable tariff surface (PAY-01/08, D-12/D-13), shared by the PaywallSheet
// (weekly limit hit) and the Profile «Магазин» section. Presentational + self-contained buy flow:
// products from GET /api/products, buy → POST /api/payments/create → openLink(confirmation_url) →
// on return (Telegram `activated` / visibilitychange) poll GET /api/me until the webhook-granted
// balance / subscription appears (D-07). It NEVER self-grants (T-07-CLIENT-GRANT) and shows honest
// copy on decline («деньги не списаны», D-13). Renders inside FlowRoot's <LazyMotion> (m.* only,
// compositor transform/opacity). All strings are brand-safe copy.ts constants (SAFE-06).

import { useEffect, useRef, useState } from "react";
import * as m from "motion/react-m";

import { useMe } from "../../hooks/useMe";
import {
  useCreatePayment,
  usePollMeUntilGranted,
  useProducts,
} from "../../hooks/usePayments";
import type { ProductOut } from "../../api/payments";
import { haptic, onActivated, openLink } from "../../lib/telegram";
import {
  HISTORY_ERROR,
  HISTORY_LOADING,
  SHOP_BUY_CTA,
  SHOP_FAILURE,
  SHOP_PENDING,
  SHOP_SUCCESS,
  SHOP_TITLE,
} from "../../reading/copy";
import { formatDays, formatRub, formatSpreads } from "../../reading/limitCopy";

type FlowStatus = "pending" | "success" | "failure";

interface ShopTariffsProps {
  /** "sheet" (inside PaywallSheet) or "profile" — only tunes spacing; the flow is identical. */
  variant?: "sheet" | "profile";
  /** The sheet host dismisses itself after a successful purchase (D-12). Absent in Profile. */
  onClose?: () => void;
}

const SUCCESS_DISMISS_MS = 1400;

/** The per-reading / duration hint under a tariff title («3 расклада» / «30 дней»). */
function tariffHint(product: ProductOut): string {
  return product.product_type === "subscription"
    ? formatDays(product.subscription_days ?? 30)
    : formatSpreads(product.spreads_amount ?? 0);
}

export function ShopTariffs({ variant = "sheet", onClose }: ShopTariffsProps) {
  const { data: products, isPending, isError } = useProducts();
  const { data: me } = useMe();
  const createPayment = useCreatePayment();
  const pollMe = usePollMeUntilGranted();

  const [flow, setFlow] = useState<{ slug: string; status: FlowStatus } | null>(
    null,
  );
  // The latest return-listener unsubscribe — cleaned on unmount so a never-returned buy never leaks.
  const stopRef = useRef<null | (() => void)>(null);
  useEffect(() => () => stopRef.current?.(), []);

  async function buy(product: ProductOut): Promise<void> {
    haptic.selection();
    setFlow({ slug: product.slug, status: "pending" });

    const isSub = product.product_type === "subscription";
    const prevBalance = me?.limits?.paid_spreads_balance ?? 0;
    const prevPeriodEnd = me?.limits?.subscription_period_end ?? null;

    let confirmationUrl: string;
    try {
      const created = await createPayment.mutateAsync(product.slug);
      confirmationUrl = created.confirmation_url;
      if (!confirmationUrl) throw new Error("missing confirmation_url");
    } catch {
      setFlow({ slug: product.slug, status: "failure" });
      return;
    }

    // Hand off to the ЮKassa-hosted page (card data never touches the app, T-07-CARD-DATA).
    openLink(confirmationUrl);

    // Detect the return, then poll GET /api/me for the webhook-granted state (D-07). Guarded so the
    // activated + visibilitychange double-fire polls at most once.
    let polled = false;
    stopRef.current?.();
    const stop = onActivated(() => {
      if (polled) return;
      polled = true;
      stop();
      void (async () => {
        const granted = await pollMe((meData) =>
          isSub
            ? // WR-04: require the window to MOVE — a re-buy while a subscription is already active
              // must not false-succeed on the already-true `subscription_active` flag (mirrors the
              // pack's `balance > prevBalance` delta). A fresh subscribe moves null → a date.
              Boolean(meData?.limits?.subscription_active) &&
              (meData?.limits?.subscription_period_end ?? null) !== prevPeriodEnd
            : (meData?.limits?.paid_spreads_balance ?? 0) > prevBalance,
        );
        setFlow({
          slug: product.slug,
          status: granted ? "success" : "failure",
        });
        if (granted && onClose) setTimeout(onClose, SUCCESS_DISMISS_MS);
      })();
    });
    stopRef.current = stop;
  }

  if (isPending) {
    return (
      <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
        {HISTORY_LOADING}
      </p>
    );
  }
  if (isError || !products) {
    return (
      <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
        {HISTORY_ERROR}
      </p>
    );
  }

  const busy = flow?.status === "pending";

  return (
    <section
      aria-label={SHOP_TITLE}
      className="flex flex-col gap-3"
      style={{ marginTop: variant === "profile" ? 0 : 4 }}
    >
      <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
        {SHOP_TITLE}
      </span>

      {products.map((product) => {
        const hint = tariffHint(product);
        return (
          <m.button
            key={product.slug}
            type="button"
            disabled={busy}
            whileTap={busy ? undefined : { scale: 0.97 }}
            onClick={() => buy(product)}
            className="panel flex items-center justify-between gap-4 p-4 text-left outline-none focus-visible:ring-2 disabled:opacity-60"
            style={{ cursor: busy ? "default" : "pointer" }}
          >
            <span className="flex flex-col">
              <span
                className="font-display text-[18px] leading-tight"
                style={{ color: "var(--deck-soft)" }}
              >
                {product.title}
              </span>
              {hint && (
                <span
                  className="text-[14px]"
                  style={{ color: "var(--color-mist-dim)" }}
                >
                  {hint}
                </span>
              )}
            </span>
            <span className="flex shrink-0 items-center gap-3">
              <span
                className="font-display text-[17px]"
                style={{ color: "var(--deck-accent)" }}
              >
                {formatRub(product.price_rub)}
              </span>
              <span
                className="rounded-full px-3 py-1.5 text-[14px]"
                style={{
                  background:
                    "color-mix(in srgb, var(--deck-accent) 16%, transparent)",
                  border:
                    "1px solid color-mix(in srgb, var(--deck-accent) 32%, transparent)",
                  color: "var(--deck-accent)",
                }}
              >
                {SHOP_BUY_CTA}
              </span>
            </span>
          </m.button>
        );
      })}

      {flow && (
        <p
          role="status"
          className="px-1 text-[15px] leading-relaxed"
          style={{
            color:
              flow.status === "failure"
                ? "var(--color-mist)"
                : "var(--deck-accent)",
          }}
        >
          {flow.status === "pending"
            ? SHOP_PENDING
            : flow.status === "success"
              ? SHOP_SUCCESS
              : SHOP_FAILURE}
        </p>
      )}
    </section>
  );
}

export default ShopTariffs;

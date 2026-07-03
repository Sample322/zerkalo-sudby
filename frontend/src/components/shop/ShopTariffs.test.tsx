import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  SHOP_BUY_CTA,
  SHOP_FAILURE,
  SHOP_SUCCESS,
  containsBannedBrandToken,
} from "../../reading/copy";
import { formatRub } from "../../reading/limitCopy";
import { ShopTariffs } from "./ShopTariffs";

// ShopTariffs renders `m.*` inside FlowRoot's <LazyMotion features={domAnimation}> in production, so
// the test supplies the same provider + a fresh QueryClient. The buy flow is exercised end-to-end
// WITHOUT a network / a real Telegram WebView: global `fetch` is stubbed (products / create / me),
// and `window.Telegram.WebApp.openLink` is a spy while `onActivated`'s visibilitychange fallback lets
// us simulate "the user returned from the ЮKassa page" by dispatching a visibilitychange event.

const CONFIRMATION_URL = "https://yoomoney.test/checkout/pay_test_1";

const PRODUCTS = [
  {
    slug: "pack_1",
    title: "Один расклад",
    description: null,
    product_type: "one_time_spreads",
    price_rub: 69,
    spreads_amount: 1,
    subscription_days: null,
  },
  {
    slug: "pack_3",
    title: "Три расклада",
    description: null,
    product_type: "one_time_spreads",
    price_rub: 169,
    spreads_amount: 3,
    subscription_days: null,
  },
  {
    slug: "sub_moon",
    title: "Лунный доступ",
    description: null,
    product_type: "subscription",
    price_rub: 299,
    spreads_amount: null,
    subscription_days: 30,
  },
];

function meResponse(paidBalance: number) {
  return {
    access_token: "t",
    user: {
      id: "u-1",
      telegram_id: 555,
      username: "buyer",
      first_name: "Гость",
      last_name: null,
      language_code: "ru",
      photo_url: null,
      is_premium_telegram: false,
      onboarding_completed: true,
    },
    limits: {
      free_weekly_limit: 3,
      free_used_this_week: 3,
      paid_spreads_balance: paidBalance,
      subscription_spreads_limit: 0,
      subscription_spreads_used: 0,
    },
    settings: {
      reversals_enabled: false,
      allow_history_personalization: false,
      onboarding_completed: true,
    },
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

interface StubState {
  meBalance: number;
  createFails: boolean;
}

/** Stub fetch: GET /api/products, POST /api/payments/create (or 500), GET /api/me (mutable balance). */
function stubFetch(state: StubState): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/api/products")) return json(PRODUCTS);
      if (u.includes("/api/payments/create")) {
        if (state.createFails) return new Response("err", { status: 500 });
        return json({
          confirmation_url: CONFIRMATION_URL,
          payment_id: "our-1",
          provider_payment_id: "yk-1",
        });
      }
      if (u.includes("/api/me")) return json(meResponse(state.meBalance));
      return json({});
    }),
  );
}

let openLinkSpy: ReturnType<typeof vi.fn>;

function renderShop(): ReactElement {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <LazyMotion features={domAnimation}>
        <ShopTariffs variant="profile" />
      </LazyMotion>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  openLinkSpy = vi.fn();
  // A minimal Telegram WebView so openLink() calls the spy and onActivated() can wire onEvent.
  window.Telegram = {
    WebApp: { openLink: openLinkSpy, onEvent: vi.fn(), offEvent: vi.fn() },
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  delete window.Telegram;
});

test("renders the tariffs with titles + RUB prices (PAY-01)", async () => {
  stubFetch({ meBalance: 0, createFails: false });
  const { getByText } = render(renderShop());

  await waitFor(() => expect(getByText("Три расклада")).toBeTruthy());
  expect(getByText("Лунный доступ")).toBeTruthy();
  expect(getByText(formatRub(69))).toBeTruthy();
  expect(getByText(formatRub(299))).toBeTruthy();
});

test("buy → createPayment → openLink(confirmation_url) (PAY-08 / T-07-CARD-DATA)", async () => {
  stubFetch({ meBalance: 0, createFails: false });
  const { getByRole } = render(renderShop());

  const buy = await waitFor(() =>
    getByRole("button", { name: /Три расклада/ }),
  );
  fireEvent.click(buy);

  // The buy opens the ЮKassa-hosted page via the returned confirmation_url (never a client URL).
  await waitFor(() =>
    expect(openLinkSpy).toHaveBeenCalledWith(CONFIRMATION_URL),
  );
});

test("after return (activated) + a granted balance → success copy (D-07)", async () => {
  const state: StubState = { meBalance: 0, createFails: false };
  stubFetch(state);
  const { getByRole, getByText } = render(renderShop());

  const buy = await waitFor(() =>
    getByRole("button", { name: /Три расклада/ }),
  );
  fireEvent.click(buy);
  await waitFor(() => expect(openLinkSpy).toHaveBeenCalled());

  // Simulate the webhook granting the pack, then the user returning to the Mini App.
  state.meBalance = 3;
  document.dispatchEvent(new Event("visibilitychange"));

  await waitFor(() => expect(getByText(SHOP_SUCCESS)).toBeTruthy());
});

test("a create failure shows honest «деньги не списаны» copy and never opens a link (D-13)", async () => {
  stubFetch({ meBalance: 0, createFails: true });
  const { getByRole, getByText } = render(renderShop());

  const buy = await waitFor(() =>
    getByRole("button", { name: /Три расклада/ }),
  );
  fireEvent.click(buy);

  await waitFor(() => expect(getByText(SHOP_FAILURE)).toBeTruthy());
  expect(openLinkSpy).not.toHaveBeenCalled();
  // The honest-failure copy carries no banned brand token (SAFE-06).
  expect(containsBannedBrandToken(SHOP_FAILURE)).toBe(false);
});

import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useSelection } from "../../stores/selection";
import {
  PROFILE_HEADER,
  PROFILE_LIMIT_LABEL,
  SETTINGS_PERSONALIZATION_EXPLAINER,
  SETTINGS_PERSONALIZATION_LABEL,
  SETTINGS_REVERSALS_LABEL,
  containsBannedBrandToken,
} from "../../reading/copy";
import { formatRemaining } from "../../reading/limitCopy";
import { ProfileScreen } from "./ProfileScreen";

// ProfileScreen renders `m.*` inside FlowRoot's <LazyMotion features={domAnimation}> in
// production, so the test supplies the same provider + a fresh QueryClient. Global `fetch` is
// stubbed (mirrors HistoryScreen.test / CatalogScreen.test) so the real fetchMe / patchSettings
// → apiFetch seam is exercised without a backend: GET /api/me returns the profile, and the
// PATCH /api/me/settings call is captured so we can assert the changed flag is the only key sent.

// A distinctive weekly-limit number we can scan the DOM for. Phase-5 D-08 asserted it was NEVER
// rendered (the count was hidden «until the limit is real»); Phase-6 D-09 UN-HIDES it, so the
// inverted test below now asserts the count «Осталось 36 из 37» IS present (free_used_this_week=1).
const FREE_WEEKLY_LIMIT = 37;

const ME_RESPONSE = {
  access_token: "test-token",
  user: {
    id: "u-1",
    telegram_id: 555,
    username: "stargazer",
    first_name: "Алина",
    last_name: "Лунная",
    language_code: "ru",
    photo_url: null,
    is_premium_telegram: false,
    onboarding_completed: true,
  },
  limits: {
    free_weekly_limit: FREE_WEEKLY_LIMIT,
    free_used_this_week: 1,
    paid_spreads_balance: 0,
    subscription_spreads_limit: 0,
    subscription_spreads_used: 0,
  },
  settings: {
    reversals_enabled: false,
    allow_history_personalization: false,
    onboarding_completed: true,
  },
};

interface PatchCall {
  url: string;
  method: string;
  body: Record<string, unknown>;
}

/** Stub fetch with server-side state: a PATCH persists into `serverSettings` so the subsequent
 *  reconcile GET /api/me reflects the change (mirrors the real backend, which commits the flag).
 *  Returns the array the test reads to assert the captured PATCH body. */
function stubFetch(): PatchCall[] {
  const patches: PatchCall[] = [];
  // The mutable server-side settings — a PATCH writes here; GET /api/me reads from here.
  const serverSettings: Record<string, boolean> = { ...ME_RESPONSE.settings };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      const u = String(url);
      const method = init?.method ?? "GET";
      if (u.includes("/api/me/settings")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        patches.push({ url: u, method, body });
        Object.assign(serverSettings, body); // persist the partial update server-side
        // The server returns the full SettingsOut reflecting the new state.
        return new Response(JSON.stringify(serverSettings), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      // The embedded ShopTariffs (D-12) fetches the catalog — return an empty shop (these tests
      // assert identity/toggles/free-count, not tariffs; an empty list renders no buy buttons).
      if (u.includes("/api/products")) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      // GET /api/me — reflects any persisted settings change (so the reconcile is honest).
      return new Response(
        JSON.stringify({ ...ME_RESPONSE, settings: { ...serverSettings } }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }),
  );
  return patches;
}

function renderProfile(): ReactElement {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <LazyMotion features={domAnimation}>
        <ProfileScreen />
      </LazyMotion>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useSelection.setState({ step: "profile", history: ["selection"] });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  useSelection.setState({ step: "onboarding", history: [] });
});

test("renders the Telegram identity + both settings toggles from GET /api/me (PROF-01/D-07)", async () => {
  stubFetch();
  const { getByText, getByRole } = render(renderProfile());

  // Header is immediate; identity + toggles resolve async.
  expect(getByText(PROFILE_HEADER)).toBeTruthy();

  await waitFor(() => expect(getByText("Алина Лунная")).toBeTruthy());

  // Both toggle labels + the personalization explainer are present.
  expect(getByText(SETTINGS_REVERSALS_LABEL)).toBeTruthy();
  expect(getByText(SETTINGS_PERSONALIZATION_LABEL)).toBeTruthy();
  expect(getByText(SETTINGS_PERSONALIZATION_EXPLAINER)).toBeTruthy();

  // Both render as switches reflecting the server settings (both OFF in the mock).
  const reversals = getByRole("switch", { name: SETTINGS_REVERSALS_LABEL });
  const personalization = getByRole("switch", { name: SETTINGS_PERSONALIZATION_LABEL });
  expect(reversals.getAttribute("aria-checked")).toBe("false");
  expect(personalization.getAttribute("aria-checked")).toBe("false");
});

test("D-09: the free-readings count block IS rendered (un-hides the Phase-5 D-08 block)", async () => {
  stubFetch();
  const { getByText } = render(renderProfile());

  await waitFor(() => expect(getByText("Алина Лунная")).toBeTruthy());

  // D-09 inverts the Phase-5 absence assertion: the un-hidden block shows the eyebrow label +
  // «Осталось 36 из 37» (free_weekly_limit=37, free_used_this_week=1 → 36 left). The free count
  // ONLY — no subscription/paid/buy (that stays Phase 7).
  expect(getByText(PROFILE_LIMIT_LABEL)).toBeTruthy();
  expect(getByText(formatRemaining(36, FREE_WEEKLY_LIMIT))).toBeTruthy();
});

test("flipping a toggle optimistically reflects it and PATCHes /api/me/settings with only that flag (PROF-02)", async () => {
  const patches = stubFetch();
  const { getByText, getByRole } = render(renderProfile());

  await waitFor(() => expect(getByText("Алина Лунная")).toBeTruthy());

  const reversals = getByRole("switch", { name: SETTINGS_REVERSALS_LABEL });
  expect(reversals.getAttribute("aria-checked")).toBe("false");

  fireEvent.click(reversals);

  // Optimistic: the switch flips ON immediately (before the PATCH resolves / reconciles).
  await waitFor(() => expect(reversals.getAttribute("aria-checked")).toBe("true"));

  // The PATCH carried ONLY the changed flag (partial update — never the whole settings object,
  // never a user_id; T-05-SPOOF). The personalization flag is untouched.
  await waitFor(() => expect(patches.length).toBeGreaterThan(0));
  const patch = patches[0];
  expect(patch.method).toBe("PATCH");
  expect(patch.url).toContain("/api/me/settings");
  expect(patch.body).toEqual({ reversals_enabled: true });
  expect(patch.body).not.toHaveProperty("allow_history_personalization");
  expect(patch.body).not.toHaveProperty("user_id");
});

test("the rendered profile copy contains no banned brand-voice token (SAFE-06 / Pitfall 6)", async () => {
  stubFetch();
  const { container, getByText } = render(renderProfile());

  await waitFor(() => expect(getByText("Алина Лунная")).toBeTruthy());
  // The personalization explainer (the riskiest copy) describes «история раскладов» / «колода
  // помнит», never the AI mechanism — the whole on-screen text is brand-safe.
  expect(containsBannedBrandToken(container.textContent ?? "")).toBe(false);
});

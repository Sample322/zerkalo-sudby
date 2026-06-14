import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  waitFor,
  type RenderResult,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { hasSeenOnboarding } from "../../hooks/useOnboardingSeen";
import { useSelection } from "../../stores/selection";
import {
  BANNED_BRAND_TOKENS,
  ONBOARDING_CTA,
  ONBOARDING_NEXT,
  ONBOARDING_SKIP,
  ONBOARDING_SLIDES,
} from "../../reading/copy";
import { OnboardingFlow } from "./OnboardingFlow";

// OnboardingFlow renders inside FlowRoot's <LazyMotion features={domAnimation}> in production,
// so its `m.*` (motion/react-m) elements require a LazyMotion provider here too. It also fires
// `usePatchSettings()` on completion (D-09 server-primary onboarding flag), which uses
// `useQueryClient`, so it must render under a fresh QueryClientProvider as well.
function renderOnboarding(): RenderResult {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LazyMotion features={domAnimation}>
        <OnboardingFlow />
      </LazyMotion>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  // Start every test PRE-onboarding: clean store step + cleared localStorage flag.
  useSelection.setState({ step: "onboarding", history: [] });
  try {
    localStorage.clear();
  } catch {
    /* private-mode safe — the hook itself never throws */
  }
  // Stub fetch so the completion PATCH (D-09) has a deterministic mock. The settings endpoint
  // echoes the patched flag (the §14 SettingsOut shape); anything else 404s.
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/api/me/settings")) {
        return new Response(
          JSON.stringify({
            reversals_enabled: false,
            allow_history_personalization: false,
            onboarding_completed: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    }),
  );
});

// The vitest config registers no global RTL auto-cleanup (no setupFiles), so each render()
// would otherwise leak its DOM into the next test (multiple OnboardingFlow instances in
// document.body → "Found multiple elements"). Unmount explicitly after every test.
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("tapping «Пропустить» persists the seen flag and advances to selection (ONB-02/ONB-04)", () => {
  const { getByText } = renderOnboarding();

  expect(hasSeenOnboarding()).toBe(false);
  expect(useSelection.getState().step).toBe("onboarding");

  fireEvent.click(getByText(ONBOARDING_SKIP));

  expect(hasSeenOnboarding()).toBe(true);
  expect(useSelection.getState().step).toBe("selection");
});

test("completing onboarding fires PATCH /api/me/settings { onboarding_completed: true } (D-09 server-primary)", async () => {
  const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
  const { getByText } = renderOnboarding();

  fireEvent.click(getByText(ONBOARDING_SKIP));

  // localStorage stays the boot fallback (written synchronously), AND the server records it.
  expect(hasSeenOnboarding()).toBe(true);
  await waitFor(() => {
    const patchCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/api/me/settings"),
    );
    expect(patchCall).toBeTruthy();
    const init = patchCall?.[1] as RequestInit | undefined;
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(String(init?.body))).toEqual({ onboarding_completed: true });
  });
});

test("advancing through all slides reaches the final CTA, which persists + advances (ONB-01/ONB-04)", () => {
  const { getByText } = renderOnboarding();

  // SLIDES = the 3 intro slides + the reversed-cards explainer = 4 slides, so 3 «Далее» taps
  // bring us to the last slide where the primary control becomes the «Сделать первый расклад» CTA.
  for (let i = 0; i < ONBOARDING_SLIDES.length; i += 1) {
    fireEvent.click(getByText(ONBOARDING_NEXT));
  }

  const cta = getByText(ONBOARDING_CTA);
  expect(cta).toBeTruthy();

  expect(hasSeenOnboarding()).toBe(false); // not yet — only the CTA tap finishes
  fireEvent.click(cta);

  expect(hasSeenOnboarding()).toBe(true);
  expect(useSelection.getState().step).toBe("selection");
});

test("the reversed-cards explainer rendered on screen is brand-safe (SAFE-06 + non-fatalistic / ONB-03)", async () => {
  const { getByText, container } = renderOnboarding();

  // Walk to the reversed-cards explainer (the final slide).
  for (let i = 0; i < ONBOARDING_SLIDES.length; i += 1) {
    fireEvent.click(getByText(ONBOARDING_NEXT));
  }

  // AnimatePresence mode="wait" mounts the entering slide only after the previous slide's
  // exit settles, so wait for the explainer copy to actually land in the DOM before scanning.
  await waitFor(() =>
    expect(/задержк|сопротивлен|напряжен/i.test(container.textContent ?? "")).toBe(
      true,
    ),
  );

  const onScreenText = container.textContent ?? "";
  // Reuse the CANONICAL ban-list helper (not an ad-hoc regex): zero AI/ИИ/нейросеть/модель/сгенерировано.
  expect(BANNED_BRAND_TOKENS.test(onScreenText)).toBe(false);
  // ONB-03: never «плохо»/«приговор» (nor беда/негатив) in the explainer framing.
  expect(/плохо|приговор|беда|негатив/i.test(onScreenText)).toBe(false);
});

test("renders nothing-broken: the first slide title + a «Пропустить» control are present", () => {
  const { getByText } = renderOnboarding();

  expect(getByText(ONBOARDING_SLIDES[0].title)).toBeTruthy();
  expect(getByText(ONBOARDING_SKIP)).toBeTruthy();
});

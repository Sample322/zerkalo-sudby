import {
  cleanup,
  fireEvent,
  render,
  waitFor,
  type RenderResult,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test } from "vitest";

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
// so its `m.*` (motion/react-m) elements require a LazyMotion provider here too. Wrap render.
function renderOnboarding(): RenderResult {
  return render(
    <LazyMotion features={domAnimation}>
      <OnboardingFlow />
    </LazyMotion>,
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
});

// The vitest config registers no global RTL auto-cleanup (no setupFiles), so each render()
// would otherwise leak its DOM into the next test (multiple OnboardingFlow instances in
// document.body → "Found multiple elements"). Unmount explicitly after every test.
afterEach(() => {
  cleanup();
});

test("tapping «Пропустить» persists the seen flag and advances to selection (ONB-02/ONB-04)", () => {
  const { getByText } = renderOnboarding();

  expect(hasSeenOnboarding()).toBe(false);
  expect(useSelection.getState().step).toBe("onboarding");

  fireEvent.click(getByText(ONBOARDING_SKIP));

  expect(hasSeenOnboarding()).toBe(true);
  expect(useSelection.getState().step).toBe("selection");
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

import {
  act,
  cleanup,
  fireEvent,
  render,
  type RenderResult,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useSelection } from "../../stores/selection";
import { RITUAL_BEATS, RITUAL_SKIP } from "../../reading/copy";
import type { MockReading } from "../../reading/types";
import { RitualScreen } from "./RitualScreen";

// RitualScreen renders inside FlowRoot's <LazyMotion features={domAnimation}> in production, so
// its `m.*` (motion/react-m) elements require a LazyMotion provider here too (mirrors the
// OnboardingFlow test). Each beat advance is timer-driven, so we drive the timeline with vitest
// fake timers and assert on the STORE transition (timing-feel / haptic-on-device stay Manual-Only
// per 03-VALIDATION — we do not assert 60fps or crossfade quality here).

// A minimal drawn reading so the art-preload branch mounts (and there is something to preload).
const FAKE_READING: MockReading = {
  question: "тест",
  topic: "love",
  deckSlug: "moon_mirror",
  spreadSlug: "three_card",
  createdAt: "2026-06-12T00:00:00.000Z",
  cards: [
    {
      name: "Шут",
      positionTitle: "Прошлое",
      orientation: "upright",
      shortMeaning: "Начало пути.",
      interpretation: "…",
      deckAccent: "…",
      shortPhrase: "…",
    },
  ],
  summary: {
    linkage: "…",
    mainFactor: "…",
    attention: "…",
    softAdvice: "…",
    closingPhrase: "…",
  },
};

function renderRitual(): RenderResult {
  return render(
    <LazyMotion features={domAnimation}>
      <RitualScreen />
    </LazyMotion>,
  );
}

beforeEach(() => {
  vi.useFakeTimers();
  // Start on the ritual step with a reading present and a clean history.
  useSelection.setState({
    step: "ritual",
    history: ["selection"],
    reading: FAKE_READING,
  });
  // The telegram seam no-ops outside Telegram; spy on it to assert completion fires the haptic.
  vi.stubGlobal("window", window);
  (window as unknown as { Telegram?: unknown }).Telegram = {
    WebApp: {
      HapticFeedback: { notificationOccurred: vi.fn() },
    },
  };
});

afterEach(() => {
  // The vitest config registers no global RTL auto-cleanup (no setupFiles) — unmount explicitly
  // so multiple RitualScreen instances never leak into the next test's document.body.
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  delete (window as unknown as { Telegram?: unknown }).Telegram;
});

test("the first beat headline renders on mount and skip is NOT active before beat 1 (D-08)", () => {
  const { getByText, queryByText } = renderRitual();

  // Beat 0 headline is on screen immediately.
  expect(getByText(RITUAL_BEATS[0])).toBeTruthy();
  // Tap-to-skip control is absent until the first beat has passed.
  expect(queryByText(RITUAL_SKIP)).toBeNull();
  // The flow has not advanced yet.
  expect(useSelection.getState().step).toBe("ritual");
});

test("advancing the timer past all beats transitions the store step to 'reveal' (READ-07)", () => {
  renderRitual();

  // Drive past all three beats (3 × BEAT_MS = 3000ms) plus a margin for the completing tick.
  act(() => {
    vi.advanceTimersByTime(RITUAL_BEATS.length * 1000 + 50);
  });

  expect(useSelection.getState().step).toBe("reveal");
});

test("after the first beat, a skip tap transitions to 'reveal' early (D-08)", () => {
  const { getByText, container } = renderRitual();

  // Advance ONE beat so skip unlocks (beat >= 1).
  act(() => {
    vi.advanceTimersByTime(1000);
  });

  // The «Пропустить» affordance is now present.
  expect(getByText(RITUAL_SKIP)).toBeTruthy();
  expect(useSelection.getState().step).toBe("ritual");

  // Tap anywhere on the canvas (the <main> carries the skip handler).
  const main = container.querySelector("main");
  expect(main).toBeTruthy();
  act(() => {
    fireEvent.click(main as Element);
  });

  expect(useSelection.getState().step).toBe("reveal");
});

test("completion invokes haptic.notify('success') (READ-07 completion haptic)", () => {
  renderRitual();

  const notify = (
    window as unknown as {
      Telegram: { WebApp: { HapticFeedback: { notificationOccurred: ReturnType<typeof vi.fn> } } };
    }
  ).Telegram.WebApp.HapticFeedback.notificationOccurred;

  act(() => {
    vi.advanceTimersByTime(RITUAL_BEATS.length * 1000 + 50);
  });

  expect(notify).toHaveBeenCalledWith("success");
  expect(useSelection.getState().step).toBe("reveal");
});

test("renders nothing-broken: the ritual canvas mounts with the first beat copy", () => {
  const { getByText } = renderRitual();
  expect(getByText(RITUAL_BEATS[0])).toBeTruthy();
});

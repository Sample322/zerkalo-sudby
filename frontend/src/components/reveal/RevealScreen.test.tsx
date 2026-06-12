import {
  cleanup,
  fireEvent,
  render,
  type RenderResult,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test } from "vitest";

import { useSelection } from "../../stores/selection";
import {
  REVEAL_OPEN_ALL,
  REVEAL_READ_MEANING,
  containsBannedBrandToken,
} from "../../reading/copy";
import type { MockReading } from "../../reading/types";
import { RevealScreen } from "./RevealScreen";

// RevealScreen renders `m.*` (motion/react-m) inside FlowRoot's <LazyMotion features={domAnimation}>
// in production, so the test supplies the same provider (mirrors the Ritual/Onboarding tests).
// We assert on REACT STATE (flip → detail/control presence), not animation timing — flip-feel and
// the per-flip haptic are Manual-Only per 03-VALIDATION.

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
      interpretation: "Прошлое подсказывает: смелый шаг открыл новую дорогу.",
      deckAccent: "Колода произносит это тихо.",
      shortPhrase: "Эта карта говорит о начале пути.",
    },
    {
      name: "Луна",
      positionTitle: "Настоящее",
      orientation: "reversed",
      shortMeaning: "Скрытое чувство.",
      interpretation: "Сейчас важно довериться внутреннему ощущению.",
      deckAccent: "В голосе колоды слышится мягкое напоминание.",
      shortPhrase: "Здесь колода показывает скрытое чувство.",
    },
    {
      name: "Звезда",
      positionTitle: "Будущее",
      orientation: "upright",
      shortMeaning: "Тихая надежда.",
      interpretation: "Впереди — спокойное прояснение и тёплый свет.",
      deckAccent: "Колода добавляет к этому тёплый оттенок.",
      shortPhrase: "Последняя карта звучит как мягкая надежда.",
    },
  ],
  summary: {
    linkage: "Карты складываются в общий узор.",
    mainFactor: "Спокойное внимание к происходящему.",
    attention: "Чувства, что проявляются не сразу.",
    softAdvice: "Двигайся мягко, без спешки.",
    closingPhrase: "Ответ всегда остаётся за тобой.",
  },
};

function renderReveal(): RenderResult {
  return render(
    <LazyMotion features={domAnimation}>
      <RevealScreen />
    </LazyMotion>,
  );
}

beforeEach(() => {
  useSelection.setState({
    step: "reveal",
    history: ["ritual"],
    reading: FAKE_READING,
  });
});

afterEach(() => {
  // No global RTL auto-cleanup (no setupFiles) — unmount explicitly to avoid cross-test leaks.
  cleanup();
  useSelection.setState({ reading: null, history: [], step: "onboarding" });
});

test("all cards start face-down and «Раскрыть все» is absent before the first flip (READ-08)", () => {
  const { getAllByLabelText, queryByText } = renderReveal();

  // One face-down «Открыть карту» tap target per spread position.
  expect(getAllByLabelText("Открыть карту")).toHaveLength(FAKE_READING.cards.length);
  // The bulk-reveal control only appears after the first flip.
  expect(queryByText(REVEAL_OPEN_ALL)).toBeNull();
});

test("tapping the first card flips it and reveals «Раскрыть все» (READ-08/D-09)", () => {
  const { getAllByLabelText, getByText } = renderReveal();

  fireEvent.click(getAllByLabelText("Открыть карту")[0]);

  // The first card's detail (name) is now shown, and «Раскрыть все» has appeared.
  expect(getByText(FAKE_READING.cards[0].name)).toBeTruthy();
  expect(getByText(REVEAL_OPEN_ALL)).toBeTruthy();
});

test("«Раскрыть все» flips the remaining cards (all card names render)", () => {
  const { getAllByLabelText, getByText } = renderReveal();

  fireEvent.click(getAllByLabelText("Открыть карту")[0]);
  fireEvent.click(getByText(REVEAL_OPEN_ALL));

  for (const card of FAKE_READING.cards) {
    expect(getByText(card.name)).toBeTruthy();
  }
});

test("a flipped card shows its short phrase BEFORE the interpretation, and the copy is brand-safe (SAFE-06)", () => {
  const { getAllByLabelText, getByText, queryByText } = renderReveal();

  fireEvent.click(getAllByLabelText("Открыть карту")[0]);

  const card = FAKE_READING.cards[0];
  // The short phrase is on screen; the interpretation is gated behind «Прочитать значение».
  expect(getByText(card.shortPhrase)).toBeTruthy();
  expect(queryByText(card.interpretation)).toBeNull();
  expect(containsBannedBrandToken(card.shortPhrase)).toBe(false);

  // Reading the meaning reveals the interpretation block.
  fireEvent.click(getByText(REVEAL_READ_MEANING));
  expect(getByText(card.interpretation)).toBeTruthy();
});

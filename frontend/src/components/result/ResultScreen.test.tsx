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
  RESULT_AGAIN_CTA,
  RESULT_HEADER,
  RESULT_HISTORY_CTA,
  RESULT_SAVE_CTA,
  containsBannedBrandToken,
} from "../../reading/copy";
import type { MockReading } from "../../reading/types";
import { ResultScreen } from "./ResultScreen";

// ResultScreen renders `m.*` inside FlowRoot's <LazyMotion features={domAnimation}> in
// production, so the test supplies the same provider. Assertions are on rendered fields +
// store transitions (the "final gather" stagger feel is Manual-Only per 03-VALIDATION).

const FAKE_READING: MockReading = {
  question: "Стоит ли мне сменить работу?",
  topic: "work",
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
      deckAccent: "Колода произносит это тихо, своим языком.",
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
    linkage: "Карты складываются в общий узор — об одном внутреннем движении.",
    mainFactor: "Главный акцент — спокойное внимание к происходящему.",
    attention: "Стоит обратить внимание на чувства, что проявляются не сразу.",
    softAdvice: "Двигайся мягко и без спешки — у темы свой ритм.",
    closingPhrase: "Ответ всегда остаётся за тобой.",
  },
};

function renderResult(): RenderResult {
  return render(
    <LazyMotion features={domAnimation}>
      <ResultScreen />
    </LazyMotion>,
  );
}

beforeEach(() => {
  useSelection.setState({
    step: "result",
    history: ["reveal"],
    reading: FAKE_READING,
    question: FAKE_READING.question ?? "",
    topic: FAKE_READING.topic,
  });
});

afterEach(() => {
  cleanup();
  useSelection.setState({
    reading: null,
    history: [],
    step: "onboarding",
    question: "",
    topic: null,
  });
});

test("renders every MockReading field — header, meta row, each card, full summary (READ-09)", () => {
  const { getByText } = renderResult();

  // Header + meta row.
  expect(getByText(RESULT_HEADER)).toBeTruthy();
  expect(getByText("Стоит ли мне сменить работу?")).toBeTruthy(); // question (text node)
  expect(getByText("work")).toBeTruthy(); // topic
  expect(getByText("moon_mirror")).toBeTruthy(); // deck
  expect(getByText("three_card")).toBeTruthy(); // spread
  expect(getByText("12.06.2026")).toBeTruthy(); // date

  // Each drawn card's fields.
  for (const card of FAKE_READING.cards) {
    expect(getByText(card.name)).toBeTruthy();
    expect(getByText(card.positionTitle)).toBeTruthy();
    expect(getByText(card.shortMeaning)).toBeTruthy();
    expect(getByText(card.interpretation)).toBeTruthy();
    expect(getByText(card.deckAccent)).toBeTruthy();
  }

  // All five summary fields.
  expect(getByText(FAKE_READING.summary.linkage)).toBeTruthy();
  expect(getByText(FAKE_READING.summary.mainFactor)).toBeTruthy();
  expect(getByText(FAKE_READING.summary.attention)).toBeTruthy();
  expect(getByText(FAKE_READING.summary.softAdvice)).toBeTruthy();
  expect(getByText(FAKE_READING.summary.closingPhrase)).toBeTruthy();
});

test("«Ещё расклад» returns to selection preserving question + topic (D-04)", () => {
  const { getByText } = renderResult();

  fireEvent.click(getByText(RESULT_AGAIN_CTA));

  const state = useSelection.getState();
  expect(state.step).toBe("selection");
  expect(state.question).toBe("Стоит ли мне сменить работу?");
  expect(state.topic).toBe("work");
});

test("«Сохранить карточку» stays a disabled, inert «скоро» stub (Phase 8)", () => {
  const { getByText } = renderResult();

  const saveBtn = getByText(RESULT_SAVE_CTA).closest("button");
  expect(saveBtn).toBeTruthy();
  expect((saveBtn as HTMLButtonElement).disabled).toBe(true);

  // Tapping the disabled stub does nothing — the flow does not advance.
  fireEvent.click(saveBtn as HTMLButtonElement);
  expect(useSelection.getState().step).toBe("result");
});

test("«История» is un-stubbed (D-10) — enabled and routes to the History step", () => {
  const { getByText } = renderResult();

  const histBtn = getByText(RESULT_HISTORY_CTA).closest("button");
  expect(histBtn).toBeTruthy();
  expect((histBtn as HTMLButtonElement).disabled).toBe(false);

  fireEvent.click(histBtn as HTMLButtonElement);
  expect(useSelection.getState().step).toBe("history");
});

test("the full rendered result copy contains no banned brand-voice token (SAFE-06)", () => {
  const { container } = renderResult();
  expect(containsBannedBrandToken(container.textContent ?? "")).toBe(false);
});

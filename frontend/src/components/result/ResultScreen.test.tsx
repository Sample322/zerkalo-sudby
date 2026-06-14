import {
  cleanup,
  fireEvent,
  render,
  type RenderResult,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useSelection } from "../../stores/selection";
import {
  NAV_BACK,
  RESULT_AGAIN_CTA,
  RESULT_HEADER,
  RESULT_HISTORY_CTA,
  RESULT_SAVE_CTA,
  containsBannedBrandToken,
} from "../../reading/copy";
import type { MockReading, ReadingOutResponse } from "../../reading/types";
import type { ReadingListItem } from "../../api/readings";
import { ResultScreen } from "./ResultScreen";

// ResultScreen renders `m.*` inside FlowRoot's <LazyMotion features={domAnimation}> in
// production, so the test supplies the same provider. Assertions are on rendered fields +
// store transitions (the "final gather" stagger feel is Manual-Only per 03-VALIDATION).
//
// The screen now calls useReadingDetail + useReadingsList unconditionally (detail mode reads
// the reading by id; live mode passes a null id). We mock the hooks module so BOTH modes work
// without a QueryClient: live tests get empty hook data (they use the store `reading`), and the
// detail test scripts the immutable body + the list-item meta.

const mockUseReadingDetail = vi.fn();
const mockUseReadingsList = vi.fn();

vi.mock("../../hooks/useReadings", () => ({
  useReadingDetail: (id: string | null) => mockUseReadingDetail(id),
  useReadingsList: () => mockUseReadingsList(),
}));

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
  // Default: empty hook data (live-mode tests rely on the store `reading`).
  mockUseReadingDetail.mockReturnValue({ data: undefined });
  mockUseReadingsList.mockReturnValue({ data: undefined });

  useSelection.setState({
    step: "result",
    history: ["reveal"],
    reading: FAKE_READING,
    question: FAKE_READING.question ?? "",
    topic: FAKE_READING.topic,
    detailReadingId: null,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  useSelection.setState({
    reading: null,
    history: [],
    step: "onboarding",
    question: "",
    topic: null,
    detailReadingId: null,
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

// ---------------------------------------------------------------------------------------
// Detail mode (HIST-03) — reopen an immutable past reading. The screen reads the fetched
// reading by id, maps it through the shared mapper, fades it in, and shows ONLY a back→History
// affordance (none of the live-flow CTAs).

const DETAIL_OUT: ReadingOutResponse = {
  reading_id: "past-1",
  status: "completed",
  cards: [
    {
      name: "Колесница",
      position_title: "Суть",
      orientation: "upright",
      short_meaning: "Движение вперёд с ясным намерением.",
      interpretation: "В центре ситуации — собранность и готовность держать курс.",
      deck_accent: "Колода произносит это тихо, своим языком.",
    },
  ],
  summary: {
    linkage: "Карта собирает фокус в одно ясное направление.",
    main_factor: "Главное сейчас — держать выбранный ритм.",
    attention: "Стоит заметить, где спешка мешает услышать себя.",
    soft_advice: "Двигайся уверенно, но без давления на себя.",
    closing_phrase: "Колода остаётся рядом: выбор всегда за тобой.",
  },
  remaining_limits: null,
};

const DETAIL_ITEM: ReadingListItem = {
  reading_id: "past-1",
  created_at: "2026-06-09T10:00:00.000Z",
  question: "Куда мне двигаться дальше?",
  deck_name: "Зеркало Луны",
  spread_name: "Одна карта",
  card_thumbnails: [""],
  summary_short: "Короткий знак о движении вперёд.",
};

function enterDetailMode(): void {
  mockUseReadingDetail.mockReturnValue({ data: DETAIL_OUT });
  mockUseReadingsList.mockReturnValue({ data: [DETAIL_ITEM] });
  useSelection.setState({
    step: "readingDetail",
    history: ["history"],
    reading: null,
    detailReadingId: "past-1",
  });
}

test("detail mode renders the fetched immutable reading + list-item meta (HIST-03)", () => {
  enterDetailMode();
  const { getByText } = renderResult();

  // Per-card + summary content comes from the immutable detail body.
  expect(getByText("Колесница")).toBeTruthy();
  expect(getByText("В центре ситуации — собранность и готовность держать курс.")).toBeTruthy();
  expect(getByText("Карта собирает фокус в одно ясное направление.")).toBeTruthy();

  // Meta (question / deck / spread / date) comes from the tapped history list item.
  expect(getByText("Куда мне двигаться дальше?")).toBeTruthy();
  expect(getByText("Зеркало Луны")).toBeTruthy();
  expect(getByText("Одна карта")).toBeTruthy();
  expect(getByText("09.06.2026")).toBeTruthy();
});

test("detail mode fetches the detail keyed by detailReadingId", () => {
  enterDetailMode();
  renderResult();
  expect(mockUseReadingDetail).toHaveBeenCalledWith("past-1");
});

test("detail mode shows a back→History affordance and NONE of the live-flow CTAs (D-11)", () => {
  enterDetailMode();
  const { queryByText, getByLabelText } = renderResult();

  // Back affordance present (returns to History via back()).
  const backBtn = getByLabelText(NAV_BACK);
  expect(backBtn).toBeTruthy();
  fireEvent.click(backBtn);
  expect(useSelection.getState().step).toBe("history");

  // None of the live result CTAs render in detail mode.
  expect(queryByText(RESULT_AGAIN_CTA)).toBeNull();
  expect(queryByText(RESULT_SAVE_CTA)).toBeNull();
  expect(queryByText(RESULT_HISTORY_CTA)).toBeNull();
});

test("detail mode shows a soft loading line while the immutable reading is in flight", () => {
  mockUseReadingDetail.mockReturnValue({ data: undefined });
  mockUseReadingsList.mockReturnValue({ data: [DETAIL_ITEM] });
  useSelection.setState({
    step: "readingDetail",
    history: ["history"],
    reading: null,
    detailReadingId: "past-1",
  });

  const { getByText, getByLabelText } = renderResult();
  // Loading line + back affordance (no card content yet).
  expect(getByText("Колода листает страницы памяти…")).toBeTruthy();
  expect(getByLabelText(NAV_BACK)).toBeTruthy();
});

test("the detail-mode rendered copy contains no banned brand-voice token (SAFE-06)", () => {
  enterDetailMode();
  const { container } = renderResult();
  expect(containsBannedBrandToken(container.textContent ?? "")).toBe(false);
});

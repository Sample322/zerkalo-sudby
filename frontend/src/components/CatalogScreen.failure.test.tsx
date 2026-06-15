// D-08 failure-UX tests for the selection screen. `createReading` is module-mocked here so
// we can script a rejection (the real seam needs a backend); this file is SEPARATE from
// CatalogScreen.test.tsx so the hoisted vi.mock does not affect the happy-path tests there.
// No live backend — fetch is stubbed for the decks/spreads catalog only.

import { cleanup, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { BANNED_BRAND_TOKENS, READING_ERROR } from "../reading/copy";
import { useSelection } from "../stores/selection";
import { renderWithClient } from "../test/renderWithClient";

// Mock the seam so the CTA's await rejects (the §9.8 / D-08 path). The factory must be
// self-contained (vi.mock is hoisted above imports). It re-exports the REAL ReadingError class
// so CatalogScreen's `err instanceof ReadingError` discriminant (D-08) still resolves to a real
// constructor under the mock — only `createReading` itself is stubbed.
vi.mock("../reading/createReading", async () => {
  const actual = await vi.importActual<typeof import("../reading/createReading")>(
    "../reading/createReading",
  );
  return { ...actual, createReading: vi.fn() };
});

// Import AFTER the mock so we get the mocked function + the component that consumes it.
import { CatalogScreen } from "./CatalogScreen";
import { createReading } from "../reading/createReading";

const createReadingMock = vi.mocked(createReading);

const DECKS = Array.from({ length: 6 }, (_, i) => ({
  slug: `deck_${i}`,
  title: `Колода ${i}`,
  subtitle: null,
  description: null,
  atmosphere: "ночь",
  tone: "мягкий",
  prompt_modifier: null,
  visual_style: {},
  recommended_topics: ["love", "general"],
  access_type: "free",
  sort_order: i,
}));

const SPREADS = Array.from({ length: 7 }, (_, i) => ({
  slug: `spread_${i}`,
  title: `Расклад ${i}`,
  description: null,
  card_count: 3,
  recommended_topics: ["love", "general"],
  positions: [
    { position_index: 1, title: "Суть", description: null, prompt_instruction: null },
  ],
}));

const RECOMMENDATION = {
  recommended_spread: SPREADS[0],
  reason: "Для темы «любовь» этот расклад открывает вопрос мягко и по существу.",
};

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const QUESTION = "Что меня ждёт в отношениях этой осенью?";

beforeEach(() => {
  useSelection.setState({
    topic: "love",
    deckSlug: "deck_0",
    spreadSlug: "spread_0",
    question: QUESTION,
    reversalsEnabled: true,
    step: "selection",
    history: [],
    reading: null,
  });
  // Default: the seam rejects (the generation-failure path). Individual tests override.
  createReadingMock.mockReset();
  createReadingMock.mockRejectedValue(new Error("колода замолчала"));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/api/spreads/recommend")) return json(RECOMMENDATION);
      if (u.includes("/api/spreads")) return json(SPREADS);
      if (u.includes("/api/decks")) return json(DECKS);
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-deck");
});

async function tapStart(getByRole: (role: string, opts: { name: string }) => HTMLElement) {
  const cta = getByRole("button", { name: "Начать расклад" }) as HTMLButtonElement;
  await waitFor(() => expect(cta.disabled).toBe(false));
  fireEvent.click(cta);
}

describe("CatalogScreen — D-08 failure UX (Повторить + Сменить колоду)", () => {
  // [test_failure_offers_retry_and_change_deck]
  test("on a failed reading the screen shows §9.8 + Повторить + Сменить колоду", async () => {
    const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
    await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

    await tapStart(getByRole);

    await waitFor(() => expect(getByText(READING_ERROR)).toBeTruthy());
    expect(getByRole("button", { name: "Повторить" })).toBeTruthy();
    expect(getByRole("button", { name: "Сменить колоду" })).toBeTruthy();

    // The failure + button copy is brand-safe (SAFE-06, incl. ИИ).
    const text = [READING_ERROR, "Повторить", "Сменить колоду"].join(" ");
    expect(BANNED_BRAND_TOKENS.test(text)).toBe(false);
  });

  // [test_no_advance_on_failure]
  test("the CTA does NOT advance to ritual on failure (stays on selection)", async () => {
    const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
    await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

    await tapStart(getByRole);

    await waitFor(() => expect(getByText(READING_ERROR)).toBeTruthy());
    expect(useSelection.getState().step).toBe("selection");
    expect(useSelection.getState().reading).toBeNull();
  });

  // [test_retry_reuses_same_params]
  test("Повторить re-runs the same request (same question/topic/deck/spread)", async () => {
    const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
    await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

    await tapStart(getByRole);
    await waitFor(() => expect(getByText(READING_ERROR)).toBeTruthy());
    expect(createReadingMock).toHaveBeenCalledTimes(1);

    fireEvent.click(getByRole("button", { name: "Повторить" }));
    await waitFor(() => expect(createReadingMock).toHaveBeenCalledTimes(2));

    // Both invocations carried the SAME params (the unchanged selection + question).
    const firstArgs = createReadingMock.mock.calls[0][0];
    const secondArgs = createReadingMock.mock.calls[1][0];
    expect(secondArgs.question).toBe(QUESTION);
    expect(secondArgs.topic).toBe("love");
    expect(secondArgs.deckSlug).toBe("deck_0");
    expect(secondArgs.spreadSlug).toBe("spread_0");
    expect(secondArgs).toEqual(firstArgs);
  });

  // [test_retry_reuses_same_params] — a retry that succeeds advances to the ritual.
  test("Повторить that succeeds writes the reading and advances to ritual", async () => {
    const succeeded = {
      question: QUESTION,
      topic: "love",
      deckSlug: "deck_0",
      spreadSlug: "spread_0",
      createdAt: new Date().toISOString(),
      cards: [
        {
          name: "Звезда",
          positionTitle: "Суть",
          orientation: "upright" as const,
          shortMeaning: "Тихая надежда.",
          interpretation: "Спокойная вера в то, что важное зреет.",
          deckAccent: "Колода говорит тихо.",
          shortPhrase: "Эта карта о центре ситуации.",
        },
      ],
      summary: {
        linkage: "Карты складываются в один поворот.",
        mainFactor: "Спокойное внимание к происходящему.",
        attention: "Чувства, что проявляются не сразу.",
        softAdvice: "Двигайся мягко и без спешки.",
        closingPhrase: "Выбор остаётся за тобой.",
      },
    };
    const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
    await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

    await tapStart(getByRole);
    await waitFor(() => expect(getByText(READING_ERROR)).toBeTruthy());

    // The next attempt resolves.
    createReadingMock.mockResolvedValueOnce(succeeded);
    fireEvent.click(getByRole("button", { name: "Повторить" }));

    await waitFor(() => expect(useSelection.getState().step).toBe("ritual"));
    const reading = useSelection.getState().reading;
    expect(reading?.question).toBe(QUESTION);
    expect(reading?.cards).toHaveLength(1);
  });

  // [test_change_deck_preserves_question]
  test("Сменить колоду keeps the question in the store (D-04) and dismisses the error", async () => {
    const { getByText, getByRole, queryByText } = renderWithClient(<CatalogScreen />);
    await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

    await tapStart(getByRole);
    await waitFor(() => expect(getByText(READING_ERROR)).toBeTruthy());

    fireEvent.click(getByRole("button", { name: "Сменить колоду" }));

    // The failure copy is dismissed; the user is back on the live selection screen.
    await waitFor(() => expect(queryByText(READING_ERROR)).toBeNull());
    // D-04: the question is preserved; the user stays on selection (deck re-selectable).
    expect(useSelection.getState().question).toBe(QUESTION);
    expect(useSelection.getState().step).toBe("selection");
    // The decks carousel is available again to pick a different deck.
    expect(getByText("Колода 1")).toBeTruthy();
  });
});

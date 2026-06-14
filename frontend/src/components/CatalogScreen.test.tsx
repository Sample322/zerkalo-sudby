import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { cleanup, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { BANNED_BRAND_TOKENS } from "../reading/copy";
import { useSelection } from "../stores/selection";
import { renderWithClient } from "../test/renderWithClient";
import { CatalogScreen } from "./CatalogScreen";

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

const REASON = "Для темы «любовь» этот расклад открывает вопрос мягко и по существу.";
const RECOMMENDATION = { recommended_spread: SPREADS[0], reason: REASON };

// GET /api/me — the persisted profile (D-09). `reversals_enabled: true` here proves the
// CatalogScreen sources a new reading's reversals from the persisted flag, NOT the local
// Zustand toggle (which the store reset leaves `false`).
const ME = {
  access_token: "tok",
  user: {
    id: "u1",
    telegram_id: 1,
    username: null,
    first_name: "Иван",
    last_name: null,
    language_code: "ru",
    photo_url: null,
    is_premium_telegram: false,
    onboarding_completed: true,
  },
  limits: {
    free_weekly_limit: 3,
    free_used_this_week: 0,
    paid_spreads_balance: 0,
    subscription_spreads_limit: 0,
    subscription_spreads_used: 0,
  },
  settings: {
    reversals_enabled: true,
    allow_history_personalization: false,
    onboarding_completed: true,
  },
};

// A completed POST /api/readings response (the §14.5 ReadingOut the seam now maps onto
// MockReading). One card, matching the single stubbed spread position ("Суть").
const COMPLETED_READING_OUT = {
  reading_id: "11111111-1111-1111-1111-111111111111",
  status: "completed",
  cards: [
    {
      name: "Звезда",
      position_title: "Суть",
      orientation: "upright",
      short_meaning: "Тихая надежда и ясность намерения.",
      interpretation: "В центре ситуации — спокойная вера в то, что важное уже зреет.",
      deck_accent: "Колода произносит это тихо, своим языком.",
    },
  ],
  summary: {
    linkage: "Карты складываются в один внутренний поворот.",
    main_factor: "Спокойное внимание к тому, что уже происходит.",
    attention: "Стоит заметить чувства, которые проявляются не сразу.",
    soft_advice: "Двигайся мягко и без спешки — у этой темы свой ритм.",
    closing_phrase: "Колода остаётся рядом: выбор всегда остаётся за тобой.",
  },
  remaining_limits: 2,
};

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  // Reset the WHOLE store (existing selection + the Phase-3 flow slice) for isolation.
  useSelection.setState({
    topic: null,
    deckSlug: null,
    spreadSlug: null,
    question: "",
    reversalsEnabled: false,
    step: "selection",
    history: [],
    reading: null,
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      const u = String(url);
      // POST /api/readings — the Phase-4 seam now hits the network; return a completed
      // §14.5 ReadingOut so createReading resolves and the happy path advances to ritual.
      if (u.includes("/api/readings")) return json(COMPLETED_READING_OUT);
      if (u.includes("/api/spreads/recommend")) return json(RECOMMENDATION);
      if (u.includes("/api/spreads")) return json(SPREADS);
      if (u.includes("/api/decks")) return json(DECKS);
      // GET /api/me — the persisted profile (D-09 reversals source).
      if (u.includes("/api/me")) return json(ME);
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => {
  // Unmount the rendered tree so multiple <CatalogScreen/> instances never accumulate in the
  // shared jsdom document (which would make getByText/getByRole match across tests).
  cleanup();
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-deck");
});

test("renders decks + spreads, re-themes on deck select, shows recommendation on topic", async () => {
  const { getByText } = renderWithClient(<CatalogScreen />);

  // Decks + spreads load (no topic chosen yet -> no recommendation banner, titles unique).
  await waitFor(() => expect(getByText("Колода 0")).toBeTruthy());
  for (const deck of DECKS) expect(getByText(deck.title)).toBeTruthy();
  for (const spread of SPREADS) expect(getByText(spread.title)).toBeTruthy();

  // UI-02 end-to-end: selecting a deck flips the root data-deck attribute.
  fireEvent.click(getByText("Колода 1"));
  await waitFor(() =>
    expect(document.documentElement.dataset.deck).toBe("deck_1"),
  );

  // SPREAD-04: choosing a topic surfaces the recommendation reason (brand-voice clean).
  fireEvent.click(getByText("Любовь"));
  await waitFor(() => expect(getByText(REASON)).toBeTruthy());
  expect(BANNED_BRAND_TOKENS.test(REASON)).toBe(false);
});

test("HOME-07: «Начать расклад» is disabled with the gating hint until topic+deck+spread are chosen", async () => {
  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  await waitFor(() => expect(getByText("Колода 0")).toBeTruthy());

  // Nothing chosen -> CTA disabled + the quiet gating hint (no dead click, no error).
  const cta = getByRole("button", { name: "Начать расклад" }) as HTMLButtonElement;
  expect(cta.disabled).toBe(true);
  expect(getByText("Выбери тему, колоду и расклад — и колода будет готова.")).toBeTruthy();
  // The gating hint copy is brand-safe (SAFE-06 via the shared ban-list, incl. ИИ).
  expect(
    BANNED_BRAND_TOKENS.test(
      "Выбери тему, колоду и расклад — и колода будет готова.",
    ),
  ).toBe(false);
});

test("HOME-07/D-05: with topic+deck+spread set, tapping the CTA builds the reading via createReading, writes it to the store `reading` slot BEFORE advancing to ritual", async () => {
  // Drive the gate directly through the store (the store-test pattern). spread_0 matches a
  // slug in the stubbed /api/spreads response so its positions are available to the handler.
  useSelection.setState({
    topic: "love",
    deckSlug: "deck_0",
    spreadSlug: "spread_0",
    question: "Что меня ждёт в отношениях этой осенью?",
  });

  // Record the ORDER of (reading, step) transitions so we can prove setReading runs before
  // the step changes to "ritual" (the downstream 03-04/05/06 contract).
  const ritualEntrySnapshot: { readingWasSet: boolean }[] = [];
  const unsubscribe = useSelection.subscribe((state) => {
    if (state.step === "ritual") {
      ritualEntrySnapshot.push({ readingWasSet: state.reading !== null });
    }
  });

  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  // Wait for the spreads query to resolve so selectedSpread is populated. Anchor on
  // "Расклад 1" — it appears ONLY in the spreads list (the recommendation banner shows
  // SPREADS[0] = "Расклад 0", so that title is ambiguous; "Расклад 1" is unique).
  await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());

  const cta = getByRole("button", { name: "Начать расклад" }) as HTMLButtonElement;
  expect(cta.disabled).toBe(false); // gate open

  fireEvent.click(cta);

  // The reading slot is populated with a fully-built MockReading and the step is now "ritual".
  await waitFor(() => expect(useSelection.getState().step).toBe("ritual"));

  const reading = useSelection.getState().reading;
  expect(reading).not.toBeNull();
  // It is the reading createReading built from our params (question passes through; one card
  // per the single spread position; brand-safe summary present).
  expect(reading?.question).toBe("Что меня ждёт в отношениях этой осенью?");
  expect(reading?.topic).toBe("love");
  expect(reading?.deckSlug).toBe("deck_0");
  expect(reading?.spreadSlug).toBe("spread_0");
  expect(reading?.cards).toHaveLength(1);
  expect(reading?.cards[0]?.positionTitle).toBe("Суть");
  expect(reading?.summary).toBeTruthy();

  // Ordering guard: at the moment step first became "ritual", the reading was ALREADY set.
  expect(ritualEntrySnapshot.length).toBeGreaterThan(0);
  expect(ritualEntrySnapshot[0].readingWasSet).toBe(true);

  unsubscribe();
});

test("D-09: a new reading's reversals_enabled is sourced from the persisted GET /api/me flag, not the local toggle", async () => {
  // The store reset leaves the LOCAL toggle `false`; the mocked `GET /api/me` says
  // reversals_enabled === true. The POST /api/readings body must carry the PERSISTED value.
  const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
  useSelection.setState({
    topic: "love",
    deckSlug: "deck_0",
    spreadSlug: "spread_0",
    question: "Что меня ждёт в отношениях этой осенью?",
    reversalsEnabled: false, // local toggle OFF — must NOT win over the persisted flag
  });

  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());
  // Let the profile query resolve so the persisted flag (not the local fallback) is in effect.
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("/api/me")),
    ).toBe(true),
  );

  const cta = getByRole("button", { name: "Начать расклад" }) as HTMLButtonElement;
  fireEvent.click(cta);

  await waitFor(() => expect(useSelection.getState().step).toBe("ritual"));

  const postCall = fetchMock.mock.calls.find(
    ([url, init]) =>
      String(url).includes("/api/readings") &&
      (init as RequestInit | undefined)?.method === "POST",
  );
  expect(postCall).toBeTruthy();
  const body = JSON.parse(String((postCall?.[1] as RequestInit).body));
  expect(body.reversals_enabled).toBe(true); // the PERSISTED flag, not the local `false`
});

test("HOME-01/02/D-13: an empty question shows no error and a 1–9-char question shows the gentle too-short hint", async () => {
  const { getByText, queryByText, getByPlaceholderText } = renderWithClient(
    <CatalogScreen />,
  );
  await waitFor(() => expect(getByText("Колода 0")).toBeTruthy());

  const textarea = getByPlaceholderText("О чём спросим колоду?") as HTMLTextAreaElement;

  // Empty question is VALID (HOME-02): the optional neutral helper shows, the too-short hint
  // does NOT (empty never triggers the "уточни" hint).
  expect(
    getByText("Можно спросить колоду о чём-то конкретном или сделать общий расклад."),
  ).toBeTruthy();
  expect(
    queryByText("Попробуй сказать чуть подробнее — так колода услышит точнее."),
  ).toBeNull();

  // 1–9 chars -> the soft too-short hint (HOME-01); the neutral empty helper is gone.
  fireEvent.change(textarea, { target: { value: "люб" } });
  await waitFor(() =>
    expect(
      getByText("Попробуй сказать чуть подробнее — так колода услышит точнее."),
    ).toBeTruthy(),
  );
  expect(
    queryByText("Можно спросить колоду о чём-то конкретном или сделать общий расклад."),
  ).toBeNull();

  // >=10 chars -> no hint at all (neither the empty helper nor the too-short hint).
  fireEvent.change(textarea, { target: { value: "люблю ли я его на самом деле?" } });
  await waitFor(() =>
    expect(
      queryByText("Попробуй сказать чуть подробнее — так колода услышит точнее."),
    ).toBeNull(),
  );
  expect(
    queryByText("Можно спросить колоду о чём-то конкретном или сделать общий расклад."),
  ).toBeNull();
});

test("T-3-01: the question is never rendered through a raw-HTML sink (no dangerouslySetInnerHTML in the source)", () => {
  // The untrusted question must be a controlled React text node only. Source-scan the
  // component file to guarantee no raw-HTML injection sink is ever introduced. Vitest runs
  // with cwd = the frontend package root, so resolve the source relative to it.
  const source = readFileSync(
    resolve(process.cwd(), "src/components/CatalogScreen.tsx"),
    "utf8",
  );
  expect(source.includes("dangerouslySetInnerHTML")).toBe(false);
  expect(source.includes(".innerHTML")).toBe(false);
});

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
    startFailure: null,
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

test("walks the wizard: topic → deck (re-themes) → spread, rendering each step's options + the recommendation", async () => {
  const { getByText, getAllByText, getByRole } = renderWithClient(<CatalogScreen />);

  // Question step is first → «Далее»; topic step → pick a topic, then «Далее» to the deck step.
  fireEvent.click(getByRole("button", { name: "Далее" }));
  fireEvent.click(getByText("Любовь"));
  fireEvent.click(getByRole("button", { name: "Далее" }));

  // Deck step: every deck renders; selecting one flips the root data-deck (UI-02). «Далее» advances.
  await waitFor(() => expect(getByText("Колода 0")).toBeTruthy());
  for (const deck of DECKS) expect(getByText(deck.title)).toBeTruthy();
  fireEvent.click(getByText("Колода 1"));
  await waitFor(() => expect(document.documentElement.dataset.deck).toBe("deck_1"));
  fireEvent.click(getByRole("button", { name: "Далее" }));

  // Spread step: every spread renders + the recommendation reason (SPREAD-04, brand-safe).
  // "Расклад 0" appears twice (recommendation banner + list) → getAllByText.
  await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());
  for (const spread of SPREADS) expect(getAllByText(spread.title).length).toBeGreaterThan(0);
  expect(getByText(REASON)).toBeTruthy();
  expect(BANNED_BRAND_TOKENS.test(REASON)).toBe(false);
});

// Walk the wizard question → topic → deck → spread → style. Each step is confirmed with «Далее»
// (no auto-advance); each step awaits its own data. Leaves the user on the final style step.
async function walkToStyle(
  getByText: (t: string) => HTMLElement,
  getByRole: (role: string, opts: { name: string }) => HTMLElement,
) {
  fireEvent.click(getByRole("button", { name: "Далее" })); // question → topic
  fireEvent.click(getByText("Любовь")); // pick topic
  fireEvent.click(getByRole("button", { name: "Далее" })); // topic → deck
  await waitFor(() => expect(getByText("Колода 0")).toBeTruthy());
  fireEvent.click(getByText("Колода 0")); // pick deck
  fireEvent.click(getByRole("button", { name: "Далее" })); // deck → spread
  await waitFor(() => expect(getByText("Расклад 1")).toBeTruthy());
  fireEvent.click(getByText("Расклад 1")); // pick spread
  fireEvent.click(getByRole("button", { name: "Далее" })); // spread → style
  await waitFor(() => expect(getByText("Бережный")).toBeTruthy());
}

test("the wizard's final step offers the 3 answer styles + an enabled «Начать расклад»", async () => {
  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  await walkToStyle(getByText, getByRole);

  // The final style step shows all 3 options; the start CTA is enabled (a spread is chosen).
  expect(getByText("Ясный")).toBeTruthy();
  expect(getByText("Бережный")).toBeTruthy();
  expect(getByText("Таинственный")).toBeTruthy();
  expect((getByRole("button", { name: "Начать расклад" }) as HTMLButtonElement).disabled).toBe(false);
});

test("HOME-07/D-05: «Начать расклад» enters the ritual IMMEDIATELY, then deposits the reading underneath it (no wait before the shuffle)", async () => {
  useSelection.setState({ question: "Что меня ждёт в отношениях этой осенью?" });

  // Record the ORDER of (reading, step) transitions to prove the ritual is entered with the
  // reading STILL NULL — the shuffle starts on tap, the slow POST runs underneath it.
  const ritualEntrySnapshot: { readingWasSet: boolean }[] = [];
  const unsubscribe = useSelection.subscribe((state) => {
    if (state.step === "ritual") {
      ritualEntrySnapshot.push({ readingWasSet: state.reading !== null });
    }
  });

  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  await walkToStyle(getByText, getByRole);

  fireEvent.click(getByRole("button", { name: "Начать расклад" }));
  // The ritual is entered right away — at that instant the reading is NOT yet built.
  await waitFor(() => expect(useSelection.getState().step).toBe("ritual"));
  expect(ritualEntrySnapshot[0].readingWasSet).toBe(false);

  // The backgrounded createReading then lands the reading into the store (ritual → reveal is
  // RitualScreen's job, exercised in its own test).
  await waitFor(() => expect(useSelection.getState().reading).not.toBeNull());
  const reading = useSelection.getState().reading;
  expect(reading?.question).toBe("Что меня ждёт в отношениях этой осенью?");
  // The result meta carries the RU labels (the slugs go to the backend; the human titles go on
  // screen) — never the English slugs. We walked Любовь / Колода 0 / Расклад 1.
  expect(reading?.topic).toBe("Любовь");
  expect(reading?.deckSlug).toBe("Колода 0");
  expect(reading?.spreadSlug).toBe("Расклад 1");
  expect(reading?.cards).toHaveLength(1);
  expect(reading?.cards[0]?.positionTitle).toBe("Суть");
  expect(reading?.summary).toBeTruthy();

  unsubscribe();
});

test("D-09: a new reading's reversals_enabled is sourced from the persisted GET /api/me flag (+ default answer_style)", async () => {
  // The store reset leaves the LOCAL toggle `false`; the mocked `GET /api/me` says
  // reversals_enabled === true. The POST /api/readings body must carry the PERSISTED value.
  const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
  useSelection.setState({
    question: "Что меня ждёт в отношениях этой осенью?",
    reversalsEnabled: false, // local toggle OFF — must NOT win over the persisted flag
  });

  const { getByText, getByRole } = renderWithClient(<CatalogScreen />);
  await walkToStyle(getByText, getByRole);
  // Let the profile query resolve so the persisted flag (not the local fallback) is in effect.
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("/api/me")),
    ).toBe(true),
  );

  fireEvent.click(getByRole("button", { name: "Начать расклад" }));
  await waitFor(() => expect(useSelection.getState().step).toBe("ritual"));

  const postCall = fetchMock.mock.calls.find(
    ([url, init]) =>
      String(url).includes("/api/readings") &&
      (init as RequestInit | undefined)?.method === "POST",
  );
  expect(postCall).toBeTruthy();
  const body = JSON.parse(String((postCall?.[1] as RequestInit).body));
  expect(body.reversals_enabled).toBe(true); // the PERSISTED flag, not the local `false`
  expect(body.answer_style).toBe("berezhny"); // the default style (no style tapped)
});

test("HOME-01/02/D-13: an empty question shows no error and a 1–9-char question shows the gentle too-short hint", async () => {
  const { getByText, queryByText, getByPlaceholderText } = renderWithClient(
    <CatalogScreen />,
  );
  // The question textarea is the first wizard step — immediately present, no navigation needed.
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

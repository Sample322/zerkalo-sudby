import { fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

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

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  useSelection.setState({ topic: null, deckSlug: null, spreadSlug: null });
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
  expect(/ai|нейросет|модель|сгенерирован/i.test(REASON)).toBe(false);
});

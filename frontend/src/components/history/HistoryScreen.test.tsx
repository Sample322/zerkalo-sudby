import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, waitFor } from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useSelection } from "../../stores/selection";
import {
  HISTORY_EMPTY,
  HISTORY_GENERAL,
  HISTORY_HEADER,
  containsBannedBrandToken,
} from "../../reading/copy";
import type { ReadingListItem } from "../../api/readings";
import { HistoryScreen } from "./HistoryScreen";

// HistoryScreen renders `m.*` inside FlowRoot's <LazyMotion features={domAnimation}> in
// production, so the test supplies the same provider + a fresh QueryClient. Global `fetch` is
// stubbed (mirrors useDecks.test) so the real fetchReadings → apiFetch seam is exercised
// (it asserts the /api/readings?limit=10 URL) without a backend.

const ITEMS: ReadingListItem[] = [
  {
    reading_id: "r-1",
    created_at: "2026-06-12T09:30:00.000Z",
    question: "Стоит ли мне сменить работу?",
    deck_name: "Зеркало Луны",
    spread_name: "Три карты",
    card_thumbnails: ["", ""],
    summary_short: "Колода советует прислушаться к внутреннему ритму.",
  },
  {
    reading_id: "r-2",
    created_at: "2026-06-10T18:00:00.000Z",
    question: null, // general reading → HISTORY_GENERAL label
    deck_name: "Лесной Оракул",
    spread_name: "Одна карта",
    card_thumbnails: [],
    summary_short: "Тихий знак о терпении.",
  },
];

function stubFetch(payload: unknown): string[] {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      calls.push(String(url));
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

function renderHistory(): ReactElement {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <LazyMotion features={domAnimation}>
        <HistoryScreen />
      </LazyMotion>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useSelection.setState({ step: "history", history: ["selection"], detailReadingId: null });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  useSelection.setState({ step: "onboarding", history: [], detailReadingId: null });
});

test("renders the header + each list item's fields (date/question/deck/spread/short summary) — HIST-02", async () => {
  const calls = stubFetch(ITEMS);
  const { getByText } = render(renderHistory());

  // Header is immediate; the list resolves async.
  expect(getByText(HISTORY_HEADER)).toBeTruthy();

  await waitFor(() => expect(getByText("Стоит ли мне сменить работу?")).toBeTruthy());

  // Item 1 fields.
  expect(getByText("12.06.2026")).toBeTruthy(); // date DD.MM.YYYY
  expect(getByText("Зеркало Луны")).toBeTruthy(); // deck
  expect(getByText("Три карты")).toBeTruthy(); // spread
  expect(getByText("Колода советует прислушаться к внутреннему ритму.")).toBeTruthy();

  // Item 2 — null question renders the «Общий расклад» label (HOME-02 / D-13).
  expect(getByText(HISTORY_GENERAL)).toBeTruthy();
  expect(getByText("Лесной Оракул")).toBeTruthy();
  expect(getByText("Тихий знак о терпении.")).toBeTruthy();

  // The fetch went through the Bearer seam to the capped list endpoint.
  expect(calls.some((u) => u.includes("/api/readings?limit=10"))).toBe(true);
});

test("the empty list renders the §9.6 empty-state copy (HIST-06)", async () => {
  stubFetch([]);
  const { getByText } = render(renderHistory());

  await waitFor(() => expect(getByText(HISTORY_EMPTY)).toBeTruthy());
});

test("the rendered history copy contains no banned brand-voice token (SAFE-06)", async () => {
  stubFetch(ITEMS);
  const { container, getByText } = render(renderHistory());

  await waitFor(() => expect(getByText("Зеркало Луны")).toBeTruthy());
  expect(containsBannedBrandToken(container.textContent ?? "")).toBe(false);
});

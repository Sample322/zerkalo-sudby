import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useSelection } from "../../stores/selection";
import { HISTORY_DELETED_NOTICE, HISTORY_DELETE_UNDO } from "../../reading/copy";
import type { ReadingListItem } from "../../api/readings";
import { HistoryScreen } from "./HistoryScreen";

// HIST-04 swipe-to-delete + undo. The card's keyboard-reachable delete button is the swipe's
// accessible twin (the swipe and the button call the SAME handler), so the test drives delete
// through it and asserts on the cache/DOM outcome — not the drag mechanics (per the plan).
// `fetch` is stubbed so the real fetchReadings / deleteReading / restoreReading → apiFetch
// seams run headless: the GET returns the list, DELETE + POST /restore return 200. We assert
// the optimistic removal, the snackbar, and that undo re-shows the item + POSTs the restore.

const ITEMS: ReadingListItem[] = [
  {
    reading_id: "r-1",
    created_at: "2026-06-12T09:30:00.000Z",
    question: "Стоит ли мне сменить работу?",
    deck_name: "Зеркало Луны",
    spread_name: "Три карты",
    card_thumbnails: [],
    summary_short: "Колода советует прислушаться к внутреннему ритму.",
  },
  {
    reading_id: "r-2",
    created_at: "2026-06-10T18:00:00.000Z",
    question: "Что мешает мне отдохнуть?",
    deck_name: "Лесной Оракул",
    spread_name: "Одна карта",
    card_thumbnails: [],
    summary_short: "Тихий знак о терпении.",
  },
];

interface FetchCall {
  url: string;
  method: string;
}

/** Stub global fetch: list GET → ITEMS; DELETE + POST /restore → 200. Returns the call log. */
function stubFetch(): FetchCall[] {
  const calls: FetchCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url: String(url), method });
      // DELETE /api/readings/{id} and POST /api/readings/{id}/restore → empty 200.
      if (method !== "GET") {
        return new Response(null, { status: 200 });
      }
      // GET list.
      return new Response(JSON.stringify(ITEMS), {
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

test("deleting a reading optimistically removes it from the list and shows the undo snackbar — HIST-04", async () => {
  const calls = stubFetch();
  const { getByText, queryByText, getAllByLabelText } = render(renderHistory());

  // The list resolves async.
  await waitFor(() => expect(getByText("Стоит ли мне сменить работу?")).toBeTruthy());
  expect(getByText("Что мешает мне отдохнуть?")).toBeTruthy();

  // Trigger delete on the FIRST card via its accessible delete button (the swipe's twin).
  const deleteButtons = getAllByLabelText("Убрать расклад из истории");
  fireEvent.click(deleteButtons[0]);

  // Optimistic remove: the first reading is gone from the rendered list immediately; the
  // second remains. The undo snackbar appears.
  await waitFor(() => expect(queryByText("Стоит ли мне сменить работу?")).toBeNull());
  expect(getByText("Что мешает мне отдохнуть?")).toBeTruthy();
  expect(getByText(HISTORY_DELETED_NOTICE)).toBeTruthy();
  expect(getByText(HISTORY_DELETE_UNDO)).toBeTruthy();

  // The DELETE went through the Bearer seam to the soft-delete endpoint.
  expect(
    calls.some((c) => c.method === "DELETE" && c.url.includes("/api/readings/r-1")),
  ).toBe(true);
});

test("«Отменить» restores the removed reading and POSTs the restore endpoint — HIST-04 undo", async () => {
  const calls = stubFetch();
  const { getByText, queryByText, getAllByLabelText } = render(renderHistory());

  await waitFor(() => expect(getByText("Стоит ли мне сменить работу?")).toBeTruthy());

  // Delete the first reading.
  const deleteButtons = getAllByLabelText("Убрать расклад из истории");
  fireEvent.click(deleteButtons[0]);
  await waitFor(() => expect(queryByText("Стоит ли мне сменить работу?")).toBeNull());

  // Undo → the reading is re-inserted into the cached list (re-rendered).
  fireEvent.click(getByText(HISTORY_DELETE_UNDO));

  await waitFor(() => expect(getByText("Стоит ли мне сменить работу?")).toBeTruthy());
  // The snackbar is dismissed once undone (AnimatePresence exit → wait it out of the DOM).
  await waitFor(() => expect(queryByText(HISTORY_DELETED_NOTICE)).toBeNull());

  // The restore went through the Bearer seam to the dedicated restore route.
  await waitFor(() =>
    expect(
      calls.some((c) => c.method === "POST" && c.url.includes("/api/readings/r-1/restore")),
    ).toBe(true),
  );
});

test("the undo window auto-dismisses after ~5s and the removal stands — HIST-04", async () => {
  vi.useFakeTimers();
  try {
    const calls = stubFetch();
    const { getByText, queryByText, getAllByLabelText } = render(renderHistory());

    // Resolve the list (advance microtasks/timers the query needs).
    await vi.waitFor(() => expect(queryByText("Стоит ли мне сменить работу?")).toBeTruthy());

    const deleteButtons = getAllByLabelText("Убрать расклад из истории");
    fireEvent.click(deleteButtons[0]);

    await vi.waitFor(() => expect(getByText(HISTORY_DELETED_NOTICE)).toBeTruthy());

    // Fast-forward past the 5s undo window → the snackbar auto-dismisses, removal stays.
    act(() => {
      vi.advanceTimersByTime(5200);
    });

    await vi.waitFor(() => expect(queryByText(HISTORY_DELETED_NOTICE)).toBeNull());
    expect(queryByText("Стоит ли мне сменить работу?")).toBeNull();
    // No restore was ever POSTed.
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  } finally {
    vi.useRealTimers();
  }
});

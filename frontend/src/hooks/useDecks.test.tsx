import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { useDecks } from "./useDecks";

const DECKS = Array.from({ length: 6 }, (_, i) => ({
  slug: `deck_${i}`,
  title: `Колода ${i}`,
  subtitle: null,
  description: null,
  atmosphere: "ночь",
  tone: "мягкий",
  prompt_modifier: null,
  visual_style: {},
  recommended_topics: ["general"],
  access_type: "free",
  sort_order: i,
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => vi.restoreAllMocks());

test("useDecks fetches 6 decks via /api/decks", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      calls.push(String(url));
      return new Response(JSON.stringify(DECKS), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );

  const { result } = renderHook(() => useDecks(), { wrapper });

  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toHaveLength(6);
  expect(calls.some((u) => u.endsWith("/api/decks"))).toBe(true);
});

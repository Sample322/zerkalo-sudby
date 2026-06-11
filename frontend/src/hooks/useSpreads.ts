import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchRecommendation, fetchSpreads } from "../api/spreads";

// Spread list keyed by the active topic/deck filters; keepPreviousData (v5 helper, NOT the
// removed boolean) keeps the old list visible while a filtered refetch is in flight.
export function useSpreads(topic?: string | null, deckSlug?: string | null) {
  return useQuery({
    queryKey: ["spreads", { topic: topic ?? null, deckSlug: deckSlug ?? null }],
    queryFn: () => fetchSpreads({ topic, deckSlug }),
    placeholderData: keepPreviousData,
  });
}

// The recommendation only makes sense once a topic is chosen, so the query is gated on it.
export function useRecommendation(topic?: string | null, deckSlug?: string | null) {
  return useQuery({
    queryKey: ["recommend", { topic: topic ?? null, deckSlug: deckSlug ?? null }],
    queryFn: () => fetchRecommendation({ topic: topic as string, deckSlug }),
    enabled: Boolean(topic),
  });
}

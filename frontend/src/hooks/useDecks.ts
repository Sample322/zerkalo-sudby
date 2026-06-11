import { useQuery } from "@tanstack/react-query";

import { fetchDecks } from "../api/decks";

// Server state lives in TanStack Query (never mirrored into Zustand). Catalog is
// near-static, so a 5-minute staleTime avoids needless refetches.
export function useDecks() {
  return useQuery({
    queryKey: ["decks"],
    queryFn: fetchDecks,
    staleTime: 5 * 60_000,
  });
}

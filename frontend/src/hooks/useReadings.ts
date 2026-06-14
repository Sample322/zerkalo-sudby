import { useQuery } from "@tanstack/react-query";

import { fetchReadingDetail, fetchReadings } from "../api/readings";

// History list as server state (TanStack Query — never mirrored into Zustand, per the locked
// architecture rule). The SINGLE stable query key `["readings", "list"]` carries no filter
// params (D-01: reverse-chronological, no filters) so 05-06's delete/restore mutations can
// target the exact same key for optimistic cache updates (Pitfall 5). A 30s staleTime keeps
// the list fresh after creating a reading without hammering the endpoint.
export function useReadingsList() {
  return useQuery({
    queryKey: ["readings", "list"],
    queryFn: fetchReadings,
    staleTime: 30_000,
  });
}

/**
 * One immutable reading (HIST-03), keyed `["readings", "detail", id]` and gated on `id`
 * (`enabled: Boolean(id)` — mirrors the useDecks enabled-gating style). The reading never
 * changes server-side (05-04 re-reads, never regenerates), so `staleTime: Infinity` means it
 * is fetched once and never restaled — re-opening the same reading is cache-instant.
 */
export function useReadingDetail(id: string | null) {
  return useQuery({
    queryKey: ["readings", "detail", id],
    queryFn: () => fetchReadingDetail(id!),
    enabled: Boolean(id),
    staleTime: Infinity,
  });
}

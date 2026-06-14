import { useQuery } from "@tanstack/react-query";

import { fetchReadings } from "../api/readings";

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

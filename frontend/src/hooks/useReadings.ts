import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteReading,
  fetchReadingDetail,
  fetchReadings,
  restoreReading,
} from "../api/readings";
import type { ReadingListItem } from "../api/readings";

/** The single stable list key — delete/restore mutations MUST target this exact tuple
 *  (Pitfall 5: same key 05-05's `useReadingsList` reads, so optimistic edits are visible). */
const LIST_KEY = ["readings", "list"] as const;

/** Snapshot carried from `onMutate` → `onError`/`onSuccess`: the pre-mutation list plus the
 *  removed item and its original index, so an undo re-inserts it exactly where it was. */
interface DeleteContext {
  prev: ReadingListItem[] | undefined;
  removed: ReadingListItem | undefined;
  index: number;
}

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

/** Variables an undo carries so the restore can re-insert the item at its original slot. */
export interface RestoreVars {
  id: string;
  item: ReadingListItem;
  index: number;
}

/**
 * Optimistic soft-delete (HIST-04 / D-03) — the canonical TanStack v5 recipe (RESEARCH
 * Pattern 3): `onMutate` cancels in-flight list fetches, snapshots `["readings","list"]`,
 * optimistically removes the item by `reading_id`, and returns the snapshot + removed item/
 * index as context; `onError` rolls the cache back to the snapshot. The DELETE itself runs in
 * the background — the UI already reflects the removal, and the server has soft-deleted, so
 * the 5s undo window and the server state agree (A3 / T-05-STALE).
 */
export function useDeleteReading() {
  const qc = useQueryClient();

  return useMutation<void, Error, string, DeleteContext>({
    mutationFn: (id) => deleteReading(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: LIST_KEY });
      const prev = qc.getQueryData<ReadingListItem[]>(LIST_KEY);
      const index = prev?.findIndex((r) => r.reading_id === id) ?? -1;
      const removed = index >= 0 ? prev?.[index] : undefined;
      if (prev) {
        qc.setQueryData<ReadingListItem[]>(
          LIST_KEY,
          prev.filter((r) => r.reading_id !== id),
        );
      }
      return { prev, removed, index };
    },
    onError: (_err, _id, context) => {
      // Roll the optimistic removal back to the exact pre-mutation snapshot (Pattern 3).
      if (context?.prev) qc.setQueryData(LIST_KEY, context.prev);
    },
  });
}

/**
 * Undo a soft-delete (HIST-04 / D-03). The `mutationFn` POSTs the restore endpoint; on success
 * it re-inserts the removed item at its original index in the SAME `["readings","list"]` cache
 * (so the list reappears without a refetch flash) and then invalidates the key to reconcile
 * with the server. On error the optimistically-removed item simply stays gone (the server is
 * authoritative — the removal already happened), and the next list fetch resolves the truth.
 */
export function useRestoreReading() {
  const qc = useQueryClient();

  return useMutation<void, Error, RestoreVars>({
    mutationFn: ({ id }) => restoreReading(id),
    onSuccess: (_data, { item, index }) => {
      const current = qc.getQueryData<ReadingListItem[]>(LIST_KEY) ?? [];
      // Re-insert only if it isn't already present (guard against a concurrent refetch).
      if (!current.some((r) => r.reading_id === item.reading_id)) {
        const at = index >= 0 && index <= current.length ? index : current.length;
        const next = [...current.slice(0, at), item, ...current.slice(at)];
        qc.setQueryData<ReadingListItem[]>(LIST_KEY, next);
      }
      void qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
}

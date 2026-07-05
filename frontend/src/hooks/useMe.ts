import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchMe, patchSettings, type MeResponse } from "../api/me";
import type { SessionSettings } from "../api/auth";

/** The single stable profile key — the optimistic settings mutation MUST target this exact
 *  tuple so its cache edits are visible to every `useMe()` reader (the Pattern-4 seam). */
const ME_KEY = ["me"] as const;

// Profile/settings as server state (TanStack Query — never mirrored into Zustand, per the locked
// architecture rule "React Query owns server state"). `GET /api/me` is near-static within a
// session, so a 60s staleTime avoids needless refetches while keeping the settings honest after
// a toggle (the mutation reconciles via settle-invalidate below).
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    staleTime: 60_000,
  });
}

/** Snapshot carried from `onMutate` → `onError`: the pre-mutation profile, so a failed PATCH
 *  rolls the optimistic toggle back to exactly what the server last confirmed. */
interface PatchContext {
  prev: MeResponse | undefined;
}

/**
 * Optimistic settings write (PROF-02 / D-09) — the canonical TanStack v5 recipe (RESEARCH
 * Pattern 4, mirroring the 05-06 delete mutation): `onMutate` cancels in-flight `["me"]`
 * fetches, snapshots the profile, optimistically merges the patched flag(s) into the cached
 * `settings` so the toggle reflects instantly, and returns the snapshot as context; `onError`
 * rolls back to that snapshot; `onSettled` invalidates `["me"]` to reconcile with the server
 * source of truth (the PATCH returns the authoritative settings). The mutation targets ONLY
 * the single `["me"]` key.
 */
export function usePatchSettings() {
  const qc = useQueryClient();

  return useMutation<SessionSettings, Error, Partial<SessionSettings>, PatchContext>({
    mutationFn: (patch) => patchSettings(patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: ME_KEY });
      const prev = qc.getQueryData<MeResponse>(ME_KEY);
      if (prev) {
        qc.setQueryData<MeResponse>(ME_KEY, {
          ...prev,
          settings: { ...prev.settings, ...patch },
        });
      }
      return { prev };
    },
    onError: (_err, _patch, context) => {
      // Roll the optimistic toggle back to the exact pre-mutation profile (Pattern 4).
      if (context?.prev) qc.setQueryData(ME_KEY, context.prev);
    },
    onSettled: () => {
      // Reconcile with the server source of truth regardless of success/failure.
      void qc.invalidateQueries({ queryKey: ME_KEY });
    },
  });
}

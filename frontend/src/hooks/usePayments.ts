// Shop hooks (PAY-01/08). Products are server state (TanStack Query — never mirrored into Zustand,
// per the locked architecture rule). The buy flow NEVER self-grants: after the user returns from the
// ЮKassa page it polls GET /api/me until the webhook-granted balance / subscription appears (D-07),
// reusing useMe's ["me"] key so every reader (Profile, Catalog) reflects the new state.

import { useCallback } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { fetchMe, type MeResponse } from "../api/me";
import {
  cancelSubscription,
  createPayment,
  fetchProducts,
  type CreatePaymentOut,
  type ProductOut,
} from "../api/payments";

const ME_KEY = ["me"] as const;

/** Default poll cadence: ~2s between checks, bounded so a never-confirmed purchase stops (D-07). */
const POLL_INTERVAL_MS = 2000;
const POLL_MAX_ATTEMPTS = 10;

/** GET /api/products as server state (near-static within a session → a generous staleTime). */
export function useProducts() {
  return useQuery<ProductOut[]>({
    queryKey: ["products"],
    queryFn: fetchProducts,
    staleTime: 5 * 60_000,
  });
}

/** The create-payment mutation — returns the ЮKassa `confirmation_url` the caller opens. */
export function useCreatePayment() {
  return useMutation<CreatePaymentOut, Error, string>({
    mutationFn: (productSlug) => createPayment(productSlug),
  });
}

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Poll GET /api/me until `predicate(me)` holds (the webhook granted) or the attempt budget runs out
 * (D-07). The FIRST check is immediate (no initial 2s wait); each fetch updates the `["me"]` cache so
 * every `useMe()` reader reflects the new balance / subscription. Resolves `true` when granted,
 * `false` on timeout — the caller shows honest failure copy on `false` (D-13). Transient fetch errors
 * are swallowed and retried within the budget (a flaky poll is not a failed purchase).
 */
export function usePollMeUntilGranted() {
  const qc = useQueryClient();

  return useCallback(
    async (
      predicate: (me: MeResponse | undefined) => boolean,
      opts: { intervalMs?: number; maxAttempts?: number } = {},
    ): Promise<boolean> => {
      const intervalMs = opts.intervalMs ?? POLL_INTERVAL_MS;
      const maxAttempts = opts.maxAttempts ?? POLL_MAX_ATTEMPTS;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          const me = await fetchMe();
          qc.setQueryData<MeResponse>(ME_KEY, me);
          if (predicate(me)) return true;
        } catch {
          // Transient network error — keep polling within the budget.
        }
        if (attempt < maxAttempts) await delay(intervalMs);
      }
      return false;
    },
    [qc],
  );
}

/** Cancel the active subscription (D-10) — access stays until period end; reconcile the ["me"] cache. */
export function useCancelSubscription() {
  const qc = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (subscriptionId) => cancelSubscription(subscriptionId),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ME_KEY });
    },
  });
}

// Session store (Zustand). Holds ONLY the client session: the JWT, the authenticated
// user, the derived available-readings count, and the auth status. Server catalog state
// (decks/spreads/history) belongs to TanStack Query in later phases and must NOT be
// duplicated here (ARCHITECTURE: React Query owns server state, Zustand holds the session).

import { create } from "zustand";
import type { AuthResponse, SessionUser } from "../api/auth";

export type AuthStatus =
  | "idle"
  | "authenticating"
  | "authenticated"
  | "error";

interface SessionState {
  jwt: string | null;
  user: SessionUser | null;
  /** Free readings still available this week + any paid balance. */
  availableReadings: number;
  status: AuthStatus;
  setAuthenticating: () => void;
  setAuthenticated: (response: AuthResponse) => void;
  setError: () => void;
}

/**
 * Available readings = remaining free weekly readings + purchased balance.
 * Clamped at zero so a fully-used week never shows a negative count.
 */
function deriveAvailableReadings(response: AuthResponse): number {
  const { limits } = response;
  const freeRemaining = Math.max(
    0,
    limits.free_weekly_limit - limits.free_used_this_week,
  );
  return freeRemaining + Math.max(0, limits.paid_spreads_balance);
}

export const useSession = create<SessionState>((set) => ({
  jwt: null,
  user: null,
  availableReadings: 0,
  status: "idle",

  setAuthenticating: () => set({ status: "authenticating" }),

  setAuthenticated: (response) =>
    set({
      jwt: response.access_token,
      user: response.user,
      availableReadings: deriveAvailableReadings(response),
      status: "authenticated",
    }),

  // On failure we clear any stale token and surface the in-character error state.
  setError: () =>
    set({ jwt: null, user: null, availableReadings: 0, status: "error" }),
}));

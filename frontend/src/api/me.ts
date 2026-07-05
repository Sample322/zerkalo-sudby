// Profile + settings API (PROF-01 / PROF-02). Reads the authenticated user's profile via
// `GET /api/me` and writes the settings flags via `PATCH /api/me/settings`, both through the
// Bearer `apiFetch` seam. The response shapes mirror the backend (backend/app/api/users.py +
// backend/app/schemas/auth.py): `GET /api/me` returns the same `{user, limits, settings}`
// projection as auth (minus the token — no schema change, PROF-01), and the PATCH returns the
// updated `SettingsOut`. We reuse the AuthResponse / SessionSettings types from api/auth.ts so
// there is one source of truth for the shape (no `any`, no duplicate interface).

import type { AuthResponse, SessionSettings } from "./auth";
import { apiFetch } from "./client";

/** Thrown when a /api/me request returns a non-2xx status (mirrors HistoryError / AuthError). */
export class MeError extends Error {
  readonly status: number;

  constructor(status: number, message = "profile request failed") {
    super(message);
    this.name = "MeError";
    this.status = status;
  }
}

/**
 * The `GET /api/me` response shape — the auth projection WITHOUT the token (the backend's
 * `MeResponse` is `AuthResponse` minus `access_token`). The `["me"]` TanStack cache is typed with
 * this so its shape is HONEST: no phantom `access_token` a future consumer could be misled by
 * (WR-07). The auth path (`authenticate`) keeps the full {@link AuthResponse} incl. the token.
 */
export type MeResponse = Omit<AuthResponse, "access_token">;

/**
 * Fetch the authenticated user's profile (PROF-01). Calls `GET /api/me` through the Bearer seam;
 * the server scopes the response to the JWT user (the client never sends a user_id). Returns
 * {@link MeResponse} — the `{user, limits, settings}` projection without the token.
 */
export async function fetchMe(): Promise<MeResponse> {
  const res = await apiFetch("/api/me");
  if (!res.ok) throw new MeError(res.status);
  return (await res.json()) as MeResponse;
}

/**
 * Partially update the authenticated user's settings flags (PROF-02 / D-09). Sends ONLY the
 * flag(s) in `patch` (the server applies just the present keys — partial update); the target is
 * always the JWT user, so the body carries no identity (threat T-05-SPOOF — a forged user_id has
 * no effect). Returns the full updated settings the caller reconciles the `["me"]` cache against.
 */
export async function patchSettings(
  patch: Partial<SessionSettings>,
): Promise<SessionSettings> {
  const res = await apiFetch("/api/me/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new MeError(res.status);
  return (await res.json()) as SessionSettings;
}

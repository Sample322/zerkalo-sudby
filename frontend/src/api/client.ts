// Authenticated fetch wrapper. Every protected call in later phases goes through this:
// it reads the JWT from the session store and attaches `Authorization: Bearer <jwt>`.
// This is the single Bearer-attachment seam — phases 2+ reuse it for /api/me, /api/decks,
// /api/readings, etc.
//
// DEPLOYMENT NOTE: `API_BASE` (VITE_API_BASE) must be the HTTPS tunnel/prod origin for
// real Telegram testing, and the Telegram WebView CSP `connect-src` MUST allow that origin
// or these fetches are blocked before they leave the WebView (RESEARCH Open Question #5).

import { API_BASE } from "../lib/api";
import { useSession } from "../stores/session";

/**
 * `fetch` against the backend with the session JWT attached as a Bearer token.
 *
 * @param path  API path beginning with `/` (e.g. `/api/me`); prefixed with `API_BASE`.
 * @param init  Standard `fetch` init; any headers provided are preserved and merged.
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const { jwt } = useSession.getState();

  const headers = new Headers(init.headers);
  if (jwt) {
    headers.set("Authorization", `Bearer ${jwt}`);
  }

  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

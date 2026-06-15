// Auth API. Forwards the raw Telegram initData to the backend, which validates the
// two-stage HMAC and issues a JWT. The response shape mirrors the backend AuthResponse
// (POST /api/auth/telegram → {access_token, user, limits, settings}); see
// backend/app/schemas/auth.py. We type only the fields the client actually consumes.

import { API_BASE } from "../lib/api";
import { getInitData } from "../lib/telegram";

/** Public user projection returned by the backend (subset we use client-side). */
export interface SessionUser {
  id: string;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string | null;
  photo_url: string | null;
  is_premium_telegram: boolean;
  onboarding_completed: boolean;
}

/** Weekly free-limit + paid balance projection. */
export interface SessionLimits {
  free_weekly_limit: number;
  free_used_this_week: number;
  paid_spreads_balance: number;
  subscription_spreads_limit: number;
  subscription_spreads_used: number;
  /**
   * The current rolling-window anchor (Phase 6 — backend `LimitsOut` serializes it; null until
   * the user's first reading anchors it). The paywall's reset moment is `week_start + 7d`; the
   * CatalogScreen reads it for the pre-emptive (freeLeft===0 on CTA tap) sheet, and the
   * authoritative `reset_at` rides on the createReading paywall-branch error for the catch path.
   */
  week_start?: string | null;
}

/** User-facing settings flags. */
export interface SessionSettings {
  reversals_enabled: boolean;
  allow_history_personalization: boolean;
  onboarding_completed: boolean;
}

export interface AuthResponse {
  access_token: string;
  user: SessionUser;
  limits: SessionLimits;
  settings: SessionSettings;
}

/** Thrown when the backend rejects authentication (e.g. missing/forged/stale initData). */
export class AuthError extends Error {
  readonly status: number;

  constructor(status: number, message = "authentication failed") {
    super(message);
    this.name = "AuthError";
    this.status = status;
  }
}

/**
 * Authenticate the current Telegram session.
 *
 * Reads the raw initData, POSTs it to the backend, and returns the parsed auth
 * response. Throws {@link AuthError} on any non-2xx response (the backend returns a
 * single generic 401 for every validation failure — no detail is leaked).
 */
export async function authenticate(): Promise<AuthResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/auth/telegram`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: getInitData() }),
    });
  } catch {
    // Network/CSP failure (e.g. WebView connect-src blocks the API origin).
    throw new AuthError(0, "network unreachable");
  }

  if (!response.ok) {
    throw new AuthError(response.status);
  }

  return (await response.json()) as AuthResponse;
}

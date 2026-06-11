// Onboarding-seen flag (ONB-04 / D-11). Persists to localStorage this phase; the
// PATCH /api/me/settings path is Phase 5. Both readers are wrapped in try/catch so a
// private-mode / storage-disabled browser never throws — worst case the onboarding
// simply re-shows (cosmetic, no trust placed in this flag; threat T-3-02 = accept).
// Mirrors the telegram.ts guard style (read the platform API, fall back gracefully).

const KEY = "zerkalo.onboarding_completed";

/** True once the user has finished or skipped onboarding. False on any storage error. */
export function hasSeenOnboarding(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

/** Mark onboarding complete. Silently no-ops if storage is unavailable. */
export function markOnboardingSeen(): void {
  try {
    localStorage.setItem(KEY, "1");
  } catch {
    /* private mode / storage disabled — show once per session, never throw */
  }
}

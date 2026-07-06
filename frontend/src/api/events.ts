// Client product analytics — fire-and-forget events to POST /api/events (ANALYTICS-01).
//
// `track()` is NEVER awaited on a UI path and swallows ALL errors: analytics must never block or
// break the flow (the backend write is itself best-effort). Properties must stay tiny + NON-PII —
// slugs / enums / counts only, NEVER the question text, names, or any personal content.

import { apiFetch } from "./client";

/** Fire-and-forget a product event. Safe to call anywhere; never throws, never blocks. */
export function track(eventName: string, properties?: Record<string, unknown>): void {
  void apiFetch("/api/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_name: eventName, properties: properties ?? {} }),
  }).catch(() => {
    /* best-effort: swallow — analytics must never surface an error */
  });
}

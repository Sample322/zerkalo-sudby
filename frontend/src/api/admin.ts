// Admin dashboard API — read-only product stats (no PII), admin-only (the backend gates on
// ADMIN_TELEGRAM_IDS and returns 403 to everyone else). Mirrors backend/app/api/admin.py
// `AdminStatsOut`.

import { apiFetch } from "./client";

/** One bucket of a distribution (a stable key, a human label, the count). */
export interface StatItem {
  key: string;
  label: string;
  count: number;
}

/** Aggregate product stats for the admin dashboard. */
export interface AdminStats {
  total_users: number;
  unlimited_users: number;
  active_users_7d: number;
  total_readings: number;
  completed_readings: number;
  failed_readings: number;
  readings_today: number;
  readings_7d: number;
  by_deck: StatItem[];
  by_topic: StatItem[];
  by_answer_style: StatItem[];
}

/** Thrown when an admin request returns a non-2xx status (403 for non-admins). */
export class AdminError extends Error {
  readonly status: number;

  constructor(status: number, message = "admin request failed") {
    super(message);
    this.name = "AdminError";
    this.status = status;
  }
}

/** Fetch the admin dashboard aggregates (admin-only; 403 otherwise). */
export async function fetchAdminStats(): Promise<AdminStats> {
  const res = await apiFetch("/api/admin/stats");
  if (!res.ok) throw new AdminError(res.status);
  return (await res.json()) as AdminStats;
}

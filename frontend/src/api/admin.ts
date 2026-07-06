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

// --- Prompt-template versioning (ADMIN-05) — the generation safety valve. ---
// Mirrors backend/app/api/admin_prompts.py. Versions coexist per slug with exactly one active;
// the operator can activate (roll back) a version or publish a new one live, no redeploy.

/** One version row of a logical prompt template. */
export interface PromptVersion {
  version: string;
  title: string;
  is_active: boolean;
  updated_at: string;
}

/** All versions of one logical prompt template, addressed by slug. */
export interface PromptSlug {
  slug: string;
  type: string;
  versions: PromptVersion[];
}

/** List every prompt template grouped by slug with its versions (admin-only). */
export async function fetchPromptSlugs(): Promise<PromptSlug[]> {
  const res = await apiFetch("/api/admin/prompts");
  if (!res.ok) throw new AdminError(res.status);
  return (await res.json()) as PromptSlug[];
}

/** Activate (roll back to) an existing version — the safety valve. */
export async function activatePromptVersion(slug: string, version: string): Promise<PromptSlug> {
  const res = await apiFetch(`/api/admin/prompts/${encodeURIComponent(slug)}/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ version }),
  });
  if (!res.ok) throw new AdminError(res.status);
  return (await res.json()) as PromptSlug;
}

/** Publish a NEW version of a template — it becomes active (create + activate). */
export async function publishPromptVersion(
  slug: string,
  body: { version: string; template_text: string; title?: string },
): Promise<PromptSlug> {
  const res = await apiFetch(`/api/admin/prompts/${encodeURIComponent(slug)}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new AdminError(res.status);
  return (await res.json()) as PromptSlug;
}

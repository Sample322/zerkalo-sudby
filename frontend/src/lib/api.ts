// Backend API client. The base URL comes from env (VITE_API_BASE), never hardcoded,
// so the same build points at localhost in dev and the HTTPS tunnel/prod origin elsewhere.

export const API_BASE: string =
  import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface HealthResult {
  db: string;
  redis: string;
}

/** Fetch the backend `/healthz` probe and return its per-dependency status. */
export async function getHealth(): Promise<HealthResult> {
  const response = await fetch(`${API_BASE}/healthz`);
  // 200 (healthy) and 503 (degraded) both carry a JSON body with db/redis status.
  const data = (await response.json()) as Partial<HealthResult>;
  return {
    db: data.db ?? "unknown",
    redis: data.redis ?? "unknown",
  };
}

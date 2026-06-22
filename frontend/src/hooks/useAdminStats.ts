import { useQuery } from "@tanstack/react-query";

import { fetchAdminStats } from "../api/admin";

/**
 * The admin dashboard stats query. Enabled only when `enabled` is true (the caller passes the
 * `is_admin` flag), so a non-admin never even fires the request. Server state lives in Query.
 */
export function useAdminStats(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: fetchAdminStats,
    enabled,
    staleTime: 30_000,
  });
}

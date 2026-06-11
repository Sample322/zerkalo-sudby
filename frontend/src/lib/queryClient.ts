import { QueryClient } from "@tanstack/react-query";

// Single shared QueryClient. The catalog (decks/spreads) is near-static, so cache
// aggressively and don't refetch on window focus; one retry covers transient blips.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

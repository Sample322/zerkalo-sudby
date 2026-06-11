// Spread catalog + recommendation API (SPREAD-01/03/04). Query strings are built with
// URLSearchParams (never manual concatenation of user-influenced values).

import { apiFetch } from "./client";
import { CatalogError } from "./decks";

export interface SpreadPosition {
  position_index: number;
  title: string;
  description: string | null;
  prompt_instruction: string | null;
}

export interface Spread {
  slug: string;
  title: string;
  description: string | null;
  card_count: number;
  recommended_topics: string[];
  positions: SpreadPosition[];
}

export interface Recommendation {
  recommended_spread: Spread;
  reason: string;
}

interface CatalogQuery {
  topic?: string | null;
  deckSlug?: string | null;
}

function buildQuery({ topic, deckSlug }: CatalogQuery): string {
  const params = new URLSearchParams();
  if (topic) params.set("topic", topic);
  if (deckSlug) params.set("deck_slug", deckSlug);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchSpreads(query: CatalogQuery = {}): Promise<Spread[]> {
  const res = await apiFetch(`/api/spreads${buildQuery(query)}`);
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as Spread[];
}

export async function fetchRecommendation(
  query: CatalogQuery & { topic: string },
): Promise<Recommendation> {
  const res = await apiFetch(`/api/spreads/recommend${buildQuery(query)}`);
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as Recommendation;
}

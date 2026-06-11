// Deck catalog API (DECK-01/03). Fetches through the Bearer `apiFetch` seam and throws a
// typed CatalogError on non-2xx (mirrors api/auth.ts). Types match the backend response_models
// (DeckOut / DeckDetailOut) — we type only the fields the client consumes.

import { apiFetch } from "./client";

export interface Deck {
  slug: string;
  title: string;
  subtitle: string | null;
  description: string | null;
  atmosphere: string | null;
  tone: string | null;
  prompt_modifier: string | null;
  visual_style: Record<string, unknown>;
  recommended_topics: string[];
  access_type: string;
  sort_order: number;
}

export type DeckDetail = Deck;

/** Thrown when a catalog request returns a non-2xx status. */
export class CatalogError extends Error {
  readonly status: number;

  constructor(status: number, message = "catalog request failed") {
    super(message);
    this.name = "CatalogError";
    this.status = status;
  }
}

export async function fetchDecks(): Promise<Deck[]> {
  const res = await apiFetch("/api/decks");
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as Deck[];
}

export async function fetchDeck(slug: string): Promise<DeckDetail> {
  const res = await apiFetch(`/api/decks/${slug}`);
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as DeckDetail;
}

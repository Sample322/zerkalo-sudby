// Client-only ritual selection: the topic / deck / spread the user is choosing.
// Server catalog lists (decks/spreads) belong to TanStack Query and must NOT be
// duplicated here (ARCHITECTURE: React Query owns server state, Zustand holds UI state).

import { create } from "zustand";

export interface SelectionState {
  topic: string | null;
  deckSlug: string | null;
  spreadSlug: string | null;
  setTopic: (topic: string | null) => void;
  setDeck: (deckSlug: string | null) => void;
  setSpread: (spreadSlug: string | null) => void;
}

export const useSelection = create<SelectionState>((set) => ({
  topic: null,
  deckSlug: null,
  spreadSlug: null,
  setTopic: (topic) => set({ topic }),
  setDeck: (deckSlug) => set({ deckSlug }),
  setSpread: (spreadSlug) => set({ spreadSlug }),
}));

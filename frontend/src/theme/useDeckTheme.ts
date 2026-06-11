import { useEffect } from "react";

import { useSelection } from "../stores/selection";

// Runtime per-deck theming (UI-02): mirror the selected deck slug onto the root
// `data-deck` attribute, which activates that deck's CSS-variable palette
// (deckThemes.css). Clearing the selection removes the deck tint.
export function useDeckTheme(): void {
  const deckSlug = useSelection((s) => s.deckSlug);
  useEffect(() => {
    document.documentElement.dataset.deck = deckSlug ?? "";
  }, [deckSlug]);
}

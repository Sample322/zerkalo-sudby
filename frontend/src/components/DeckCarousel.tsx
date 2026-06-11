import type { Deck } from "../api/decks";
import { DeckCard } from "./DeckCard";

interface DeckCarouselProps {
  decks: Deck[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

// Horizontally scroll-snapping row of deck tiles, sized for a 360-430px column. Maps over
// the fetched decks (never hardcoded); renders nothing-broken on an empty array.
export function DeckCarousel({ decks, selectedSlug, onSelect }: DeckCarouselProps) {
  if (decks.length === 0) return null;

  return (
    <div
      role="list"
      className="flex snap-x snap-mandatory gap-4 overflow-x-auto px-1 pb-2"
    >
      {decks.map((deck) => (
        <div role="listitem" key={deck.slug}>
          <DeckCard
            deck={deck}
            active={deck.slug === selectedSlug}
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  );
}

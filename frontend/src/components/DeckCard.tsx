import * as m from "motion/react-m";

import type { Deck } from "../api/decks";
import { CardArt } from "./CardArtFallback";

const TOPIC_LABELS: Record<string, string> = {
  love: "любовь",
  work: "работа",
  money: "деньги",
  choice: "выбор",
  day: "день",
  self_reflection: "саморефлексия",
  general: "общий вопрос",
};

interface DeckCardProps {
  deck: Deck;
  active: boolean;
  onSelect: (slug: string) => void;
}

// A premium-dark glass deck tile. The atmospheric CardArt fallback stands in for art (none
// seeded yet), floating once chosen, so a deck still reads intentionally. Selecting accents it
// and (via the screen's useDeckTheme) re-tints the whole surface — the core «один вопрос, разные
// колоды» feel.
export function DeckCard({ deck, active, onSelect }: DeckCardProps) {
  const suits = deck.recommended_topics
    .map((t) => TOPIC_LABELS[t] ?? t)
    .slice(0, 3)
    .join(" · ");

  return (
    <m.button
      type="button"
      onClick={() => onSelect(deck.slug)}
      aria-pressed={active}
      whileHover={{ scale: 1.03, y: -3 }}
      whileTap={{ scale: 0.97 }}
      className="panel flex w-56 shrink-0 snap-center flex-col items-center gap-4 p-5 text-center"
      style={{
        borderColor: active
          ? "color-mix(in srgb, var(--deck-accent) 60%, transparent)"
          : undefined,
        boxShadow: active
          ? "inset 0 1px 0 color-mix(in srgb, var(--deck-soft) 12%, transparent), 0 0 0 1px color-mix(in srgb, var(--deck-accent) 50%, transparent), 0 18px 46px -18px color-mix(in srgb, var(--deck-glow) 70%, transparent)"
          : undefined,
      }}
    >
      <CardArt src={null} alt={deck.title} glyph={deck.title.charAt(0)} float={active} />
      <span className="flex flex-col items-center gap-1">
        <span className="font-display metal-text text-[21px] leading-tight">{deck.title}</span>
        {deck.atmosphere && (
          <span className="text-[15px]" style={{ color: "color-mix(in srgb, var(--color-mist) 82%, transparent)" }}>
            {deck.atmosphere}
          </span>
        )}
        {deck.tone && (
          <span className="text-[14px] italic" style={{ color: "var(--color-mist-dim)" }}>
            {deck.tone}
          </span>
        )}
        {suits && (
          <span className="eyebrow mt-2" style={{ letterSpacing: "0.14em" }}>
            Для: {suits}
          </span>
        )}
      </span>
    </m.button>
  );
}

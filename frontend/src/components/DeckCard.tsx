import { motion } from "motion/react";

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

// A premium-dark glass deck tile. The atmospheric CardArt fallback stands in for art
// (none seeded in Phase 2), so a deck still reads intentionally. Selecting accents it and
// (via the screen's useDeckTheme) re-tints the whole surface.
export function DeckCard({ deck, active, onSelect }: DeckCardProps) {
  const suits = deck.recommended_topics
    .map((t) => TOPIC_LABELS[t] ?? t)
    .slice(0, 3)
    .join(" · ");

  return (
    <motion.button
      type="button"
      onClick={() => onSelect(deck.slug)}
      aria-pressed={active}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className="flex w-56 shrink-0 snap-center flex-col gap-3 rounded-2xl border p-4 text-left"
      style={{
        background:
          "linear-gradient(155deg, color-mix(in srgb, var(--deck-bg) 88%, transparent), color-mix(in srgb, var(--deck-deep) 72%, transparent))",
        borderColor: active
          ? "var(--deck-accent)"
          : "color-mix(in srgb, var(--deck-soft) 22%, transparent)",
        boxShadow: active
          ? "0 0 0 1px var(--deck-accent), 0 14px 44px -18px var(--deck-accent)"
          : "0 12px 32px -22px #000",
      }}
    >
      <span className="self-center">
        <CardArt src={null} alt={deck.title} glyph={deck.title.charAt(0)} />
      </span>
      <span className="flex flex-col gap-1">
        <span className="text-lg font-semibold" style={{ color: "var(--deck-soft)" }}>
          {deck.title}
        </span>
        {deck.atmosphere && (
          <span className="text-xs opacity-70">{deck.atmosphere}</span>
        )}
        {deck.tone && <span className="text-xs italic opacity-60">{deck.tone}</span>}
        {suits && (
          <span className="mt-1 text-xs" style={{ color: "var(--deck-accent)" }}>
            Для: {suits}
          </span>
        )}
      </span>
    </motion.button>
  );
}

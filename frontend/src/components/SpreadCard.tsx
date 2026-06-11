import type { Spread } from "../api/spreads";

interface SpreadCardProps {
  spread: Spread;
  recommended?: boolean;
  onSelect?: (slug: string) => void;
}

// A spread tile: title, card count, and its position titles. A "рекомендуем" accent marks
// the topic-recommended spread.
export function SpreadCard({ spread, recommended = false, onSelect }: SpreadCardProps) {
  const positions = spread.positions.map((p) => p.title).join(" · ");

  return (
    <button
      type="button"
      onClick={() => onSelect?.(spread.slug)}
      className="flex w-full flex-col gap-2 rounded-xl border p-4 text-left transition-transform duration-200 hover:scale-[1.01] focus-visible:outline-none focus-visible:ring-2 active:scale-[0.99]"
      style={{
        borderColor: recommended
          ? "var(--deck-accent)"
          : "color-mix(in srgb, var(--deck-soft) 18%, transparent)",
        background: "color-mix(in srgb, var(--deck-bg) 70%, transparent)",
      }}
    >
      <span className="flex items-center justify-between gap-2">
        <span className="text-base font-semibold" style={{ color: "var(--deck-soft)" }}>
          {spread.title}
        </span>
        {recommended && (
          <span
            className="rounded-full px-2 py-0.5 text-xs"
            style={{
              background: "color-mix(in srgb, var(--deck-accent) 18%, transparent)",
              color: "var(--deck-accent)",
            }}
          >
            рекомендуем
          </span>
        )}
      </span>
      <span className="text-xs opacity-70">{spread.card_count} карты</span>
      {positions && <span className="text-xs opacity-60">{positions}</span>}
    </button>
  );
}

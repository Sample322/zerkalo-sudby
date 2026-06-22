import type { Spread } from "../api/spreads";

interface SpreadCardProps {
  spread: Spread;
  recommended?: boolean;
  onSelect?: (slug: string) => void;
}

// A spread tile on ritual glass: title (display), card count + position titles (quiet eyebrow),
// and a metal «рекомендуем» mark on the topic-recommended spread. The selected affordance (a
// gold ring) is applied by the parent wrapper in CatalogScreen.
export function SpreadCard({ spread, recommended = false, onSelect }: SpreadCardProps) {
  const positions = spread.positions.map((p) => p.title).join(" · ");

  return (
    <button
      type="button"
      onClick={() => onSelect?.(spread.slug)}
      className="panel flex w-full flex-col gap-2 p-4 text-left transition-transform duration-200 hover:scale-[1.01] focus-visible:outline-none focus-visible:ring-2 active:scale-[0.99]"
    >
      <span className="flex items-center justify-between gap-3">
        <span
          className="font-display text-[19px] leading-tight"
          style={{ color: "var(--deck-soft)" }}
        >
          {spread.title}
        </span>
        {recommended && (
          <span
            className="eyebrow shrink-0 rounded-full px-2.5 py-1"
            style={{
              background: "color-mix(in srgb, var(--deck-accent) 16%, transparent)",
              border: "1px solid color-mix(in srgb, var(--deck-accent) 32%, transparent)",
              color: "var(--deck-accent)",
              letterSpacing: "0.16em",
            }}
          >
            рекомендуем
          </span>
        )}
      </span>
      <span className="eyebrow" style={{ color: "var(--color-mist-dim)", letterSpacing: "0.18em" }}>
        {spread.card_count} карты
      </span>
      {positions && (
        <span className="text-[15px] italic" style={{ color: "color-mix(in srgb, var(--color-mist) 80%, transparent)" }}>
          {positions}
        </span>
      )}
    </button>
  );
}

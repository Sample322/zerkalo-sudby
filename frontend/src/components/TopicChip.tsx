interface TopicChipProps {
  topic: string;
  label: string;
  active: boolean;
  onSelect: (topic: string) => void;
}

// A pill that selects a question topic. Active = a struck-metal pill (deck soft→accent fill,
// ink text, a soft glow); inactive = a ghost on glass. Hover/focus/active are compositor-only.
export function TopicChip({ topic, label, active, onSelect }: TopicChipProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(topic)}
      aria-pressed={active}
      className="font-display whitespace-nowrap rounded-full px-4 py-2 text-[13px] tracking-wide transition-transform duration-200 hover:scale-[1.05] focus-visible:outline-none focus-visible:ring-2 active:scale-95"
      style={
        active
          ? {
              color: "var(--deck-bg)",
              background: "linear-gradient(180deg, var(--deck-soft), var(--deck-accent))",
              boxShadow:
                "0 8px 20px color-mix(in srgb, var(--deck-accent) 30%, transparent), inset 0 1px 0 rgba(255,255,255,0.38)",
              border: "1px solid transparent",
            }
          : {
              color: "var(--deck-soft)",
              background: "color-mix(in srgb, var(--deck-deep) 40%, transparent)",
              border: "1px solid color-mix(in srgb, var(--deck-soft) 26%, transparent)",
            }
      }
    >
      {label}
    </button>
  );
}

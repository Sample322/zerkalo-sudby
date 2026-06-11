interface TopicChipProps {
  topic: string;
  label: string;
  active: boolean;
  onSelect: (topic: string) => void;
}

// A pill that selects a question topic. Active state is accented with the live deck palette;
// hover/focus/active are deliberately designed (compositor-friendly transform only).
export function TopicChip({ topic, label, active, onSelect }: TopicChipProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(topic)}
      aria-pressed={active}
      className="whitespace-nowrap rounded-full border px-4 py-2 text-sm transition-transform duration-200 hover:scale-[1.05] focus-visible:outline-none focus-visible:ring-2 active:scale-95"
      style={
        active
          ? {
              borderColor: "var(--deck-accent)",
              color: "var(--deck-accent)",
              background: "color-mix(in srgb, var(--deck-accent) 14%, transparent)",
            }
          : {
              borderColor: "color-mix(in srgb, var(--deck-soft) 28%, transparent)",
              color: "var(--deck-soft)",
            }
      }
    >
      {label}
    </button>
  );
}

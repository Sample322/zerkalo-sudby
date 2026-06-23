// Unified motion tokens — mirror the CSS motion grammar (index.css `--dur-*` / `--ease-*`) so
// every animation in the app reads as ONE system, not ad-hoc values. Durations are in seconds
// (motion's unit); easings are cubic-bezier arrays; springs are reusable physics configs. Usage
// stays compositor-only (transform / opacity) everywhere per the perf rules.

/** Durations in seconds (CSS mirrors: fast 220ms / normal 460ms / slow 900ms). */
export const DURATION = {
  fast: 0.22,
  normal: 0.46,
  slow: 0.9,
  ritual: 1.1,
} as const;

/** Cubic-bezier easings. `softOut` = --ease-out-expo, `mystical` = --ease-ritual. */
export const EASE = {
  standard: [0.4, 0, 0.2, 1] as const,
  softOut: [0.16, 1, 0.3, 1] as const,
  mystical: [0.22, 1, 0.36, 1] as const,
};

/** Reusable spring configs for physical, weighty motion (cards, sheets). */
export const SPRING = {
  soft: { type: "spring", stiffness: 180, damping: 24 } as const,
  card: { type: "spring", stiffness: 260, damping: 26 } as const,
  modal: { type: "spring", stiffness: 320, damping: 32 } as const,
};

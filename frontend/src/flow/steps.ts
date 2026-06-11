// The flow step-machine token (D-02). A string-literal union — NOT an enum — per the
// TS coding-style (mirrors session.ts `AuthStatus`). A single `step` field in the
// selection store drives one `<AnimatePresence>` switch (onboarding → selection →
// ritual → reveal → result); see flow/FlowRoot.tsx.

export type Step = "onboarding" | "selection" | "ritual" | "reveal" | "result";

/** The five steps in their natural forward order. */
export const STEP_ORDER: readonly Step[] = [
  "onboarding",
  "selection",
  "ritual",
  "reveal",
  "result",
] as const;

/**
 * The next step in the natural forward order, or the same step if already last.
 * Pure helper (no store coupling) so it is unit-testable without React. The store's
 * `goTo` is the real navigator (it also records history for the in-app back, D-03);
 * `next` is a convenience for linear advances.
 */
export function next(step: Step): Step {
  const i = STEP_ORDER.indexOf(step);
  if (i < 0 || i >= STEP_ORDER.length - 1) return step;
  return STEP_ORDER[i + 1];
}

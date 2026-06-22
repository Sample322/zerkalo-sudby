// Client-only ritual selection + the flow step-machine (D-02). The user's topic / deck /
// spread choices, the free-text question, the reversals toggle, the `step` state-machine
// with history-backed in-app back (D-03), and the single ephemeral mock `reading` slot.
//
// Server catalog lists (decks/spreads/recommendation) belong to TanStack Query and must
// NOT be duplicated here (ARCHITECTURE: React Query owns server state, Zustand holds UI
// state). The mock `reading` is ephemeral client state — it lives ONLY here, NEVER in Query.

import { create } from "zustand";
import type { Step } from "../flow/steps";
import type { MockReading } from "../reading/types";

/** Min/max bounds for the free-text question (HOME-01 / D-13). Empty is explicitly valid. */
export const QUESTION_MIN = 10;
export const QUESTION_MAX = 500;

/** The answer-style preference (Ясный / Бережный / Таинственный) — tunes how the reading sounds. */
export type AnswerStyle = "yasny" | "berezhny" | "tainstvenny";
export const DEFAULT_ANSWER_STYLE: AnswerStyle = "berezhny";

/** Discriminated result of validating the question text (pure, React-free). */
export type QuestionValidity =
  | { status: "valid" }
  | { status: "tooShort" };

export interface SelectionState {
  // --- existing selection (kept verbatim) ---
  topic: string | null;
  deckSlug: string | null;
  spreadSlug: string | null;
  setTopic: (topic: string | null) => void;
  setDeck: (deckSlug: string | null) => void;
  setSpread: (spreadSlug: string | null) => void;
  /** Answer-style preference (default Бережный). Recorded on the reading + tracked for the MVP A/B. */
  answerStyle: AnswerStyle;
  setAnswerStyle: (style: AnswerStyle) => void;

  // --- flow slice (Phase 3) ---
  /** The free-text question (HOME-01/02). Empty string = general reading (D-13). */
  question: string;
  /** Local reversals toggle (D-07). Off => all upright. */
  reversalsEnabled: boolean;
  /** The current screen the flow machine is on (D-02). */
  step: Step;
  /** Previous steps, newest last — backs the in-app back affordance (D-03). */
  history: Step[];
  /**
   * The single ephemeral mock reading (D-05). Writer: plan 03-03 (selection CTA).
   * Readers: plans 03-04/05 (reveal) and 03-06 (result). `null` until built; the
   * Phase-4 backend reading swaps in here unchanged (createReading return type).
   */
  reading: MockReading | null;
  /**
   * Which past reading the detail view (`readingDetail` step) renders (Phase 5, D-02/D-10).
   * Set by the History list when a list-item card is tapped, then `goTo("readingDetail")`.
   * `null` when no detail is open. 05-06 reads this to fetch + render the immutable reading
   * via the reused ResultScreen; this plan only owns the slot + setter (the writer seam).
   */
  detailReadingId: string | null;

  setQuestion: (q: string) => void;
  toggleReversals: () => void;
  /** Navigate to a step, recording the current step on `history` for back (D-03). */
  goTo: (s: Step) => void;
  /** Pop `history` and restore the prior step (the in-app back, D-03). No-op if empty. */
  back: () => void;
  /** D-04: return to selection KEEPING question + topic; deck/spread stay re-selectable. */
  startReadingAgain: () => void;
  /** Deposit (or clear) the freshly-built mock reading; touches ONLY `reading`. */
  setReading: (reading: MockReading | null) => void;
  /** Set which past reading the detail view renders (Phase 5); touches ONLY `detailReadingId`. */
  setDetailReadingId: (id: string | null) => void;
}

/**
 * Question validity (HOME-01 / HOME-02 / D-13), as a pure helper so it is unit-testable
 * without React (mirrors session.ts `deriveAvailableReadings`):
 *   - empty            -> valid  (general reading; no hint)
 *   - 1..9 chars       -> tooShort (gentle "уточни" hint)
 *   - >= 10 chars      -> valid
 * The upper bound is enforced by clamping at the input (`setQuestion`), so a stored
 * question is never longer than QUESTION_MAX and never reads as "too short" past 10.
 */
export function questionValidity(question: string): QuestionValidity {
  const len = question.trim().length;
  if (len === 0) return { status: "valid" };
  if (len < QUESTION_MIN) return { status: "tooShort" };
  return { status: "valid" };
}

/**
 * HOME-07 start gate: the ritual can begin only when a topic, a deck, AND a spread are
 * all chosen. Pure (operates on a slice) so it is testable without React.
 */
export function canStart(
  state: Pick<SelectionState, "topic" | "deckSlug" | "spreadSlug">,
): boolean {
  return Boolean(state.topic && state.deckSlug && state.spreadSlug);
}

export const useSelection = create<SelectionState>((set) => ({
  topic: null,
  deckSlug: null,
  spreadSlug: null,
  setTopic: (topic) => set({ topic }),
  setDeck: (deckSlug) => set({ deckSlug }),
  setSpread: (spreadSlug) => set({ spreadSlug }),
  answerStyle: "berezhny",
  setAnswerStyle: (answerStyle) => set({ answerStyle }),

  question: "",
  reversalsEnabled: false,
  step: "onboarding",
  history: [],
  reading: null,
  detailReadingId: null,

  // Clamp at the upper bound so stored text never exceeds QUESTION_MAX (HOME-01).
  setQuestion: (q) => set({ question: q.slice(0, QUESTION_MAX) }),
  toggleReversals: () =>
    set((s) => ({ reversalsEnabled: !s.reversalsEnabled })),

  goTo: (s) =>
    set((state) => ({ step: s, history: [...state.history, state.step] })),

  back: () =>
    set((state) => {
      if (state.history.length === 0) return {};
      const history = state.history.slice(0, -1);
      const prev = state.history[state.history.length - 1];
      return { step: prev, history };
    }),

  // D-04: back to selection without clearing question/topic (deck/spread re-selectable).
  // `reading` is intentionally NOT cleared — the prior reading stays available until the
  // next build overwrites it via setReading.
  startReadingAgain: () =>
    set((state) => ({
      step: "selection",
      history: [...state.history, state.step],
    })),

  // Cross-plan writer/reader seam — mutates ONLY `reading`.
  setReading: (reading) => set({ reading }),

  // Phase-5 writer/reader seam — mutates ONLY `detailReadingId` (which past reading the
  // detail view renders). HistoryScreen writes it before goTo("readingDetail"); 05-06 reads it.
  setDetailReadingId: (id) => set({ detailReadingId: id }),
}));

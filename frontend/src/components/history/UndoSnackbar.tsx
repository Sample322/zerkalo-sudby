import { useEffect } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { getContentSafeAreaInsets } from "../../lib/telegram";
import { HISTORY_DELETED_NOTICE, HISTORY_DELETE_UNDO } from "../../reading/copy";

// UndoSnackbar — the HIST-04 / D-03 undo affordance for swipe-to-delete. A `motion`
// `AnimatePresence` element (NO toast library — RESEARCH Don't-Hand-Roll) that fades/slides in
// when `open`, runs a 5s timer, and calls `onDismiss` when the window lapses (the optimistic
// removal then stands — the server already soft-deleted). «Отменить» calls `onUndo`. The timer
// is cleared on unmount and whenever `open` flips, so an undo (which closes the snackbar)
// cancels the pending auto-dismiss. Motion is compositor-only (opacity + translateY).

/** How long the undo stays offered before the removal becomes final (~5s, D-03). */
const UNDO_WINDOW_MS = 5000;

interface UndoSnackbarProps {
  /** Whether a deletion is currently undoable (one snackbar at a time). */
  open: boolean;
  /** «Отменить» — restore the reading. */
  onUndo: () => void;
  /** The 5s window lapsed (or the snackbar was dismissed) — finalize the removal. */
  onDismiss: () => void;
}

export function UndoSnackbar({ open, onUndo, onDismiss }: UndoSnackbarProps) {
  const insets = getContentSafeAreaInsets();

  // Auto-dismiss after the undo window. Re-armed whenever `open` (re)opens; cleared on
  // unmount/close so an undo cancels the pending timer (no double-fire).
  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(onDismiss, UNDO_WINDOW_MS);
    return () => window.clearTimeout(timer);
  }, [open, onDismiss]);

  return (
    <AnimatePresence>
      {open && (
        <m.div
          // Pinned above the safe-area bottom; centered, mobile-width.
          className="fixed inset-x-0 bottom-0 z-50 mx-auto flex w-full max-w-md items-center justify-between gap-4 px-6"
          style={{ paddingBottom: 16 + insets.bottom }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 16 }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          role="status"
          aria-live="polite"
        >
          <div
            className="flex w-full items-center justify-between gap-4 rounded-2xl px-4 py-3"
            style={{
              background: "color-mix(in srgb, var(--deck-deep) 92%, transparent)",
              border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
              color: "var(--deck-soft)",
            }}
          >
            <span className="text-sm">{HISTORY_DELETED_NOTICE}</span>
            <m.button
              type="button"
              whileTap={{ scale: 0.95 }}
              onClick={onUndo}
              className="shrink-0 rounded-full px-3 py-1 text-sm font-semibold outline-none focus-visible:ring-2"
              style={{
                background: "transparent",
                border: "1px solid var(--deck-accent)",
                color: "var(--deck-accent)",
                cursor: "pointer",
              }}
            >
              {HISTORY_DELETE_UNDO}
            </m.button>
          </div>
        </m.div>
      )}
    </AnimatePresence>
  );
}

export default UndoSnackbar;

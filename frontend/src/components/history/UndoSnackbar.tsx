import { useEffect, useRef } from "react";
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

  // Keep the latest onDismiss in a ref so the auto-dismiss timer depends ONLY on `open` — a parent
  // passing an inline (non-memoized) onDismiss (HistoryScreen does) would otherwise re-run this
  // effect on every re-render (e.g. when the delete mutation settles), CLEARING + RE-ARMING the 5s
  // timer and measuring the window from the last render instead of from open. Ref-ing the callback
  // arms the timer exactly once per open (the component owns its contract, no parent memoization).
  const onDismissRef = useRef(onDismiss);
  onDismissRef.current = onDismiss;

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => onDismissRef.current(), UNDO_WINDOW_MS);
    return () => window.clearTimeout(timer);
  }, [open]);

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
          <div className="panel flex w-full items-center justify-between gap-4 px-4 py-3" style={{ color: "var(--deck-soft)" }}>
            <span className="text-[15px] italic">{HISTORY_DELETED_NOTICE}</span>
            <m.button
              type="button"
              whileTap={{ scale: 0.95 }}
              onClick={onUndo}
              className="pill-ghost shrink-0 px-4 py-1.5 text-[14px] outline-none focus-visible:ring-2"
              style={{ color: "var(--deck-accent)", borderColor: "color-mix(in srgb, var(--deck-accent) 50%, transparent)" }}
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

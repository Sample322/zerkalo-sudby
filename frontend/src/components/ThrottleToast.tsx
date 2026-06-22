// ThrottleToast — Surface 2 (D-08). The TRANSIENT counterpart to the persistent PaywallSheet:
// a glass pill that surfaces «Колода переводит дыхание…» on an HTTP-429 burst (the 06-03 Redis
// gate), then AUTO-DISMISSES after ~3.75s — no buttons, no user action. It is visually and
// behaviorally DISTINCT from the paywall sheet (transient vs persistent; "one breath, then
// retry" vs "done for the week, returns on {date}") so the two limit states are never conflated.
//
// It reuses the self-contained setTimeout + AnimatePresence pattern proven in UndoSnackbar
// (no toast library — zero new dependency): the timer is re-armed whenever `open` (re)opens and
// cleared on unmount/close so a fresh trip never double-fires. Motion is compositor-only
// (opacity + translateY). NO red/alarm hue — a throttle is a gentle "slow down", not an error.
// The message is the brand-safe copy.ts constant (SAFE-06); a React text node only (T-06-17).

import { useEffect } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { getContentSafeAreaInsets } from "../lib/telegram";
import { THROTTLE_MESSAGE } from "../reading/copy";

/** Auto-dismiss window (~3.75s, within the UI-SPEC ~3.5–4s band). */
const THROTTLE_WINDOW_MS = 3750;

interface ThrottleToastProps {
  /** Whether the transient throttle pill is shown. */
  open: boolean;
  /** The auto-dismiss window lapsed (or it was closed) — clear the toast. */
  onDismiss: () => void;
}

export function ThrottleToast({ open, onDismiss }: ThrottleToastProps) {
  const insets = getContentSafeAreaInsets();

  // Auto-dismiss after the window. Re-armed whenever `open` (re)opens; cleared on unmount/close
  // so a rapid re-trip (open→open) restarts the timer cleanly with no double-fire.
  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(onDismiss, THROTTLE_WINDOW_MS);
    return () => window.clearTimeout(timer);
  }, [open, onDismiss]);

  return (
    <AnimatePresence>
      {open && (
        <m.div
          // A centered, mobile-width pill pinned above the safe-area bottom — distinct placement
          // and shape from the full-width bottom-sheet (D-08 distinction).
          className="fixed inset-x-0 bottom-0 z-50 mx-auto flex w-full max-w-md justify-center px-6"
          style={{ paddingBottom: 24 + insets.bottom }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          role="status"
          aria-live="polite"
        >
          <div
            className="panel flex items-center gap-3 px-5 py-3.5 text-center text-[16px] italic leading-relaxed"
            style={{ color: "var(--deck-soft)" }}
          >
            <span aria-hidden="true" style={{ color: "var(--deck-accent)" }}>✦</span>
            {THROTTLE_MESSAGE}
          </div>
        </m.div>
      )}
    </AnimatePresence>
  );
}

export default ThrottleToast;

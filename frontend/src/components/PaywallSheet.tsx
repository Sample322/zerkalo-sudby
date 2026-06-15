// PaywallSheet — Surface 1 (LIMIT-01, D-03/D-04/D-05). A SOFT, in-character bottom-sheet that
// claims the fixed CTA-band region when the weekly free quota is exhausted: «закончились…
// вернутся через N дней», with the reset moment as the single accent-tinted hopeful focal point
// (D-04 — the antidote to a dead-end), a quiet «скоро ещё» note, and a dismiss affordance. It is
// PERSISTENT until dismissed (the distinction from the transient ThrottleToast, D-08).
//
// HARD constraints (UI-SPEC): NO price, NO payment/purchase affordance of any kind, NO dead CTA
// (payments are Phase 7); NO red/alarm hue (a blocked free reading is a neutral, honest state,
// not an error); NO live-ticking clock (a static «через N дней» / date is correct). Every string
// is the brand-safe copy.ts constant + the pure formatReset helper (SAFE-06). Dismissing
// preserves the caller's question + selections — the sheet never clears anything.
//
// Renders inside FlowRoot's <LazyMotion features={domAnimation}>, so motion uses `m.*` from
// "motion/react-m" with compositor-only opacity/translateY. Safe-area bottom padding is the same
// dynamic Math.max(getSafeAreaInsets, getContentSafeAreaInsets) the CTA band computes — sourced
// from the Telegram SDK insets, not CSS viewport units. Copy renders as React text nodes only
// (no dangerouslySetInnerHTML, T-06-17).

import { useEffect } from "react";
import type { CSSProperties } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { getContentSafeAreaInsets, getSafeAreaInsets, haptic } from "../lib/telegram";
import { formatReset } from "../reading/limitCopy";
import {
  PAYWALL_DISMISS,
  PAYWALL_RESET_LEAD,
  PAYWALL_SOON_NOTE,
  PAYWALL_TITLE,
} from "../reading/copy";

/** The established glass language (mirrors ProfileScreen/ResultScreen) for the sheet panel. */
const GLASS: CSSProperties = {
  background:
    "linear-gradient(155deg, color-mix(in srgb, var(--deck-bg) 88%, transparent), color-mix(in srgb, var(--deck-deep) 72%, transparent))",
  borderTop: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
};

/** The locked Phase-3 screen-enter motion token (compositor-only). */
const SHEET_TRANSITION = { duration: 0.28, ease: [0.16, 1, 0.3, 1] } as const;

interface PaywallSheetProps {
  /** Whether the weekly-exhaustion sheet is shown (persistent until dismissed). */
  open: boolean;
  /** The per-user reopen moment (`reset_at` = week_start + 7d) — fuels the D-04 countdown. */
  resetAt?: string | null;
  /** Dismiss the sheet (tap the dismiss glyph or the scrim). Preserves question + selections. */
  onDismiss: () => void;
}

export function PaywallSheet({ open, resetAt, onDismiss }: PaywallSheetProps) {
  // A soft selection haptic on open — never notify("warning"/"error"); a blocked reading is not
  // an alarm (UI-SPEC discouraged-haptic note). No-op outside Telegram.
  useEffect(() => {
    if (open) haptic.selection();
  }, [open]);

  // Dynamic, additive safe-area bottom padding (the exact CTA-band pattern), from the Telegram
  // SDK insets rather than CSS viewport units, so it clears the home indicator.
  const bottomInset = Math.max(
    getSafeAreaInsets().bottom,
    getContentSafeAreaInsets().bottom,
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Dimmed scrim — focuses attention without hiding the live deck canvas; animate
              opacity ONLY. Tap-to-dismiss. aria-hidden: the dismiss button is the labelled control. */}
          <m.div
            className="fixed inset-0 z-40"
            style={{ background: "color-mix(in srgb, var(--deck-bg) 70%, transparent)" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={SHEET_TRANSITION}
            aria-hidden="true"
            onClick={onDismiss}
          />

          <m.div
            className="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-3xl px-6 pt-8"
            style={{ ...GLASS, paddingBottom: 24 + bottomInset, color: "var(--deck-soft)" }}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={SHEET_TRANSITION}
            role="dialog"
            aria-modal="true"
            aria-label={PAYWALL_TITLE}
          >
            {/* Contents top→bottom, each block separated by lg (24px). */}
            <div className="flex flex-col gap-6">
              <h2
                className="text-2xl font-semibold leading-tight"
                style={{ color: "var(--deck-soft)" }}
              >
                {PAYWALL_TITLE}
              </h2>

              {/* The reset line — the reset value is the single accent-tinted hopeful focal
                  point (D-04). A static phrase, never a ticking clock. */}
              <p className="text-base leading-relaxed" style={{ color: "var(--deck-soft)" }}>
                {PAYWALL_RESET_LEAD}
                <span style={{ color: "var(--deck-accent)" }}>{formatReset(resetAt ?? "")}</span>
              </p>

              {/* The quiet «скоро ещё» note — no pressure, no price, no button (D-03). */}
              <p
                className="text-base leading-relaxed opacity-70"
                style={{ color: "var(--deck-soft)" }}
              >
                {PAYWALL_SOON_NOTE}
              </p>

              {/* Dismiss glyph — the only affordance (no purchase control). The icon-button
                  hit-area is ≥44px; accent-tinted; focus-ring resolves to accent. */}
              <div className="flex justify-end">
                <m.button
                  type="button"
                  whileTap={{ scale: 0.94 }}
                  onClick={onDismiss}
                  aria-label={PAYWALL_DISMISS}
                  className="grid h-11 w-11 place-items-center rounded-full text-lg outline-none focus-visible:ring-2"
                  style={{
                    background: "color-mix(in srgb, var(--deck-deep) 60%, transparent)",
                    border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
                    color: "var(--deck-accent)",
                    cursor: "pointer",
                  }}
                >
                  <span aria-hidden="true">✕</span>
                </m.button>
              </div>
            </div>
          </m.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default PaywallSheet;

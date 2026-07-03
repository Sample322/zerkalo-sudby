// PaywallSheet — Surface 1 (LIMIT-01, D-03/D-04/D-05). A SOFT, in-character bottom-sheet shown
// when the weekly free quota is exhausted: «закончились… вернутся через N дней», with the reset
// moment as the single accent-tinted hopeful focal point (D-04), a quiet «скоро ещё» note, and a
// dismiss affordance. PERSISTENT until dismissed (the distinction from the transient ThrottleToast).
//
// HARD constraints (UI-SPEC): NO price, NO payment affordance, NO dead CTA (payments are Phase 7);
// NO red/alarm hue; NO live-ticking clock. Every string is the brand-safe copy.ts constant + the
// pure formatReset helper. Dismissing preserves the caller's question + selections.
//
// Renders inside FlowRoot's <LazyMotion features={domAnimation}>, motion is compositor-only
// (opacity/translateY). Safe-area bottom padding from the Telegram SDK insets, not CSS units.

import { useEffect } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { getContentSafeAreaInsets, getSafeAreaInsets, haptic } from "../lib/telegram";
import { formatReset } from "../reading/limitCopy";
import {
  PAYWALL_DISMISS,
  PAYWALL_RESET_LEAD,
  PAYWALL_TITLE,
} from "../reading/copy";
import { ShopTariffs } from "./shop/ShopTariffs";

const SHEET_TRANSITION = { duration: 0.28, ease: [0.16, 1, 0.3, 1] } as const;

interface PaywallSheetProps {
  /** Whether the weekly-exhaustion sheet is shown (persistent until dismissed). */
  open: boolean;
  /** The per-user reopen moment (`reset_at` = week_start + 7d) — fuels the D-04 hopeful line. */
  resetAt?: string | null;
  /** Dismiss the sheet (tap the dismiss glyph or the scrim). Preserves question + selections. */
  onDismiss: () => void;
}

export function PaywallSheet({ open, resetAt, onDismiss }: PaywallSheetProps) {
  // A soft selection haptic on open — never notify("warning"/"error"); a blocked reading is not
  // an alarm. No-op outside Telegram.
  useEffect(() => {
    if (open) haptic.selection();
  }, [open]);

  const bottomInset = Math.max(getSafeAreaInsets().bottom, getContentSafeAreaInsets().bottom);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Dimmed scrim — focuses attention; animate opacity only. Tap-to-dismiss. */}
          <m.div
            className="fixed inset-0 z-40"
            style={{ background: "color-mix(in srgb, var(--deck-bg) 72%, transparent)", backdropFilter: "blur(2px)" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={SHEET_TRANSITION}
            aria-hidden="true"
            onClick={onDismiss}
          />

          <m.div
            className="panel-altar fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md px-7 pt-5"
            style={{
              borderRadius: "26px 26px 0 0",
              paddingBottom: 24 + bottomInset,
              color: "var(--deck-soft)",
            }}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={SHEET_TRANSITION}
            role="dialog"
            aria-modal="true"
            aria-label={PAYWALL_TITLE}
          >
            {/* Gold grip ornament. */}
            <div className="mx-auto mb-6 h-1 w-12 rounded-full" style={{ background: "color-mix(in srgb, var(--deck-accent) 50%, transparent)" }} />

            <div className="flex flex-col gap-6">
              <h2 className="font-display metal-text text-[26px] leading-tight">{PAYWALL_TITLE}</h2>

              {/* The reset line — the reset value is the single accent-tinted hopeful focal point. */}
              <p className="text-[17px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
                {PAYWALL_RESET_LEAD}
                <span className="font-display" style={{ color: "var(--deck-accent)" }}>
                  {formatReset(resetAt ?? "")}
                </span>
              </p>

              {/* Real tariffs replace the old «скоро» note (D-12): buy → openLink → poll /api/me. */}
              <ShopTariffs variant="sheet" onClose={onDismiss} />

              <div className="flex justify-end">
                <m.button
                  type="button"
                  whileTap={{ scale: 0.94 }}
                  onClick={onDismiss}
                  aria-label={PAYWALL_DISMISS}
                  className="grid h-11 w-11 place-items-center rounded-full text-lg outline-none focus-visible:ring-2"
                  style={{
                    background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
                    border: "1px solid color-mix(in srgb, var(--deck-accent) 28%, transparent)",
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

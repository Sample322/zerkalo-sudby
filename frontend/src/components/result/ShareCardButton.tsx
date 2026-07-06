// ShareCardButton — the privacy-safe share affordance on the result (UI-06). Renders the reading to
// an image client-side (deck + spread + cards + closing line, NEVER the question) and shares it via
// the Web Share API with a download fallback. In-voice copy only; no banned brand tokens.

import { useState } from "react";
import * as m from "motion/react-m";

import { renderShareCard, shareOrDownload } from "../../lib/shareCard";
import { haptic } from "../../lib/telegram";
import { SHARE_BUTTON, SHARE_FAILED, SHARE_SAVED_HINT } from "../../reading/copy";
import type { MockReading } from "../../reading/types";

type ShareState = "idle" | "working" | "saved" | "error";

export function ShareCardButton({ reading }: { reading: MockReading }) {
  const [state, setState] = useState<ShareState>("idle");

  async function handleShare(): Promise<void> {
    if (state === "working") return;
    setState("working");
    haptic.selection();
    try {
      const blob = await renderShareCard({
        // `deckSlug`/`spreadSlug` carry the RU display titles here (see createReading meta).
        deckName: reading.deckSlug,
        spreadName: reading.spreadSlug,
        cards: reading.cards.map((c) => ({
          name: c.name,
          positionTitle: c.positionTitle,
          orientation: c.orientation,
        })),
        summary: reading.summary.closingPhrase,
      });
      const outcome = await shareOrDownload(blob, "zerkalo-sudby.png");
      setState(outcome === "downloaded" ? "saved" : "idle");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="mt-6 flex flex-col items-center gap-2">
      <m.button
        type="button"
        whileTap={{ scale: 0.96 }}
        disabled={state === "working"}
        onClick={handleShare}
        className="pill-ghost px-6 py-3 text-[15px] outline-none focus-visible:ring-2"
        style={{ cursor: state === "working" ? "default" : "pointer" }}
      >
        {SHARE_BUTTON}
      </m.button>
      {state === "saved" && (
        <p className="text-center text-[13px] italic" style={{ color: "var(--color-mist-dim)" }}>
          {SHARE_SAVED_HINT}
        </p>
      )}
      {state === "error" && (
        <p className="text-center text-[13px] italic" style={{ color: "var(--color-mist-dim)" }}>
          {SHARE_FAILED}
        </p>
      )}
    </div>
  );
}

export default ShareCardButton;

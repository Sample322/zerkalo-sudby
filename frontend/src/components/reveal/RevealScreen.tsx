import { useState } from "react";
import { stagger } from "motion/react";
import * as m from "motion/react-m";

import { track } from "../../api/events";
import { useSelection } from "../../stores/selection";
import { getSafeAreaInsets } from "../../lib/telegram";
import {
  ORIENTATION_LABELS,
  REVEAL_OPEN_ALL,
  REVEAL_READ_MEANING,
  REVEAL_TO_RESULT,
} from "../../reading/copy";
import type { MockReadingCard } from "../../reading/types";
import { FlipCard } from "./FlipCard";

// READ-08 / D-09 — the flip-reveal screen. One face-down FlipCard per spread position; tapping
// flips it. After the FIRST flip a «Раскрыть все» control staggers the rest in a cascade. Each
// flipped card shows name + orientation + a short in-character phrase BEFORE the interpretation,
// which «Прочитать значение» reveals. All animation is compositor-only via `m.*`.

function cardKey(card: MockReadingCard): string {
  return `${card.positionTitle}|${card.name}`;
}

const detailsContainer = {
  rest: {},
  reveal: { transition: { delayChildren: stagger(0.12) } },
};

const detailItem = {
  rest: { opacity: 0, y: 8 },
  reveal: { opacity: 1, y: 0 },
};

export function RevealScreen() {
  const reading = useSelection((s) => s.reading);
  const goTo = useSelection((s) => s.goTo);

  const [flipped, setFlipped] = useState<ReadonlySet<string>>(new Set());
  const [read, setRead] = useState<ReadonlySet<string>>(new Set());

  // Reachable only once selection built a reading; guard with an element (not null) for the
  // FlowRoot `() => Element` registry contract.
  if (!reading) {
    return <main className="flex min-h-full items-center justify-center" />;
  }

  const cards = reading.cards;
  const anyFlipped = flipped.size > 0;
  const allFlipped = flipped.size === cards.length;

  const flipOne = (key: string) => {
    if (!flipped.has(key)) track("card_revealed"); // ANALYTICS-01 (best-effort, on a new flip)
    setFlipped((prev) => {
      if (prev.has(key)) return prev;
      const next = new Set(prev);
      next.add(key);
      return next;
    });
  };

  const revealAll = () => setFlipped(new Set(cards.map(cardKey)));

  const readMeaning = (key: string) =>
    setRead((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });

  return (
    <main className="flex min-h-full flex-col px-6 pb-28 pt-8" style={{ color: "var(--deck-soft)" }}>
      <header className="flex flex-col items-center gap-2 text-center">
        <span className="eyebrow">Расклад открывается</span>
        <h1 className="font-display metal-text text-[28px] leading-tight">Коснись каждой карты</h1>
      </header>

      <m.div
        variants={detailsContainer}
        initial="rest"
        animate={anyFlipped ? "reveal" : "rest"}
        className="mt-9 grid gap-9"
      >
        {cards.map((card) => {
          const key = cardKey(card);
          const isFlipped = flipped.has(key);
          const isRead = read.has(key);
          return (
            <div key={key} className="flex flex-col items-center gap-3 text-center">
              <p className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
                {card.positionTitle}
              </p>

              <FlipCard card={{ name: card.name }} flipped={isFlipped} onFlip={() => flipOne(key)} />

              {isFlipped && (
                <m.div variants={detailItem} className="flex flex-col items-center gap-2" style={{ maxWidth: 330 }}>
                  <p className="font-display metal-text text-[23px] leading-tight">{card.name}</p>
                  <p className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
                    {ORIENTATION_LABELS[card.orientation]}
                  </p>
                  {/* Short in-character phrase BEFORE the interpretation (READ-08). */}
                  <p className="text-[17px] italic" style={{ color: "var(--deck-soft)" }}>
                    {card.shortPhrase}
                  </p>

                  {isRead ? (
                    <p className="text-[16px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
                      {card.interpretation}
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={() => readMeaning(key)}
                      className="font-display mt-1 text-[14px] tracking-wide underline-offset-4 hover:underline"
                      style={{ background: "transparent", border: "none", color: "var(--deck-accent)", cursor: "pointer" }}
                    >
                      {REVEAL_READ_MEANING}
                    </button>
                  )}
                </m.div>
              )}
            </div>
          );
        })}
      </m.div>

      {/* «Раскрыть все» — only after the first flip, gone once all are open. */}
      {anyFlipped && !allFlipped && (
        <m.button
          type="button"
          whileTap={{ scale: 0.96 }}
          onClick={revealAll}
          className="pill-ghost mt-9 self-center px-6 py-2.5 text-[15px]"
        >
          {REVEAL_OPEN_ALL}
        </m.button>
      )}

      {/* Sticky «К итогу» — pill on a gradient floor, clear of the home indicator. */}
      <div
        className="fixed inset-x-0 bottom-0 z-20 mx-auto w-full max-w-md px-6 pt-3"
        style={{
          paddingBottom: 16 + getSafeAreaInsets().bottom,
          background: "linear-gradient(to top, var(--deck-bg) 62%, transparent)",
        }}
      >
        <m.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={() => goTo("result")}
          className="pill-primary w-full px-4 py-4 text-[18px] outline-none focus-visible:ring-2"
        >
          {REVEAL_TO_RESULT}
        </m.button>
      </div>
    </main>
  );
}

export default RevealScreen;

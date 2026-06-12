import { useState } from "react";
import { stagger } from "motion/react";
import * as m from "motion/react-m";

import { useSelection } from "../../stores/selection";
import {
  NAV_BACK,
  ORIENTATION_LABELS,
  REVEAL_OPEN_ALL,
  REVEAL_READ_MEANING,
  REVEAL_TO_RESULT,
} from "../../reading/copy";
import type { MockReadingCard } from "../../reading/types";
import { FlipCard } from "./FlipCard";

// READ-08 / D-09 — the flip-reveal screen. One face-down FlipCard per spread position;
// tapping flips it. After the FIRST flip a «Раскрыть все» control staggers the rest in a
// cascade (delayChildren: stagger). Each flipped card shows its name + orientation + a short
// in-character phrase BEFORE the interpretation, which a «Прочитать значение» reveals. All
// animation is compositor-only via `m.*` (rendered inside FlowRoot's LazyMotion). FlowRoot
// already routes step==="reveal" here, so this file never touches FlowRoot.

// A stable per-card key (NOT the array index — index keys break AnimatePresence exit
// detection and re-key on reorder; position+name is unique within a spread and stable).
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
  const back = useSelection((s) => s.back);

  const [flipped, setFlipped] = useState<ReadonlySet<string>>(new Set());
  const [read, setRead] = useState<ReadonlySet<string>>(new Set());

  // The reveal step is only reachable once selection built a reading; guard defensively.
  if (!reading) return null;

  const cards = reading.cards;
  const anyFlipped = flipped.size > 0;
  const allFlipped = flipped.size === cards.length;

  const flipOne = (key: string) =>
    setFlipped((prev) => {
      if (prev.has(key)) return prev;
      const next = new Set(prev);
      next.add(key);
      return next;
    });

  const revealAll = () => setFlipped(new Set(cards.map(cardKey)));

  const readMeaning = (key: string) =>
    setRead((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });

  return (
    <main
      className="flex min-h-full flex-col px-6 pb-28 pt-6"
      style={{ color: "var(--deck-soft)" }}
    >
      <button
        type="button"
        onClick={back}
        className="self-start text-sm opacity-70"
        style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
      >
        {NAV_BACK}
      </button>

      <m.div
        variants={detailsContainer}
        initial="rest"
        animate={anyFlipped ? "reveal" : "rest"}
        className="mt-4 grid gap-8"
      >
        {cards.map((card) => {
          const key = cardKey(card);
          const isFlipped = flipped.has(key);
          const isRead = read.has(key);
          return (
            <div key={key} className="flex flex-col items-center gap-3 text-center">
              <p className="text-sm opacity-60">{card.positionTitle}</p>

              <FlipCard
                card={{ name: card.name }}
                flipped={isFlipped}
                onFlip={() => flipOne(key)}
              />

              {isFlipped && (
                <m.div
                  variants={detailItem}
                  className="flex flex-col items-center gap-2"
                  style={{ maxWidth: 320 }}
                >
                  <p
                    className="text-lg font-semibold"
                    style={{ color: "var(--deck-accent)" }}
                  >
                    {card.name}
                  </p>
                  <p className="text-xs uppercase tracking-wide opacity-60">
                    {ORIENTATION_LABELS[card.orientation]}
                  </p>
                  {/* Short in-character phrase BEFORE the interpretation (READ-08). */}
                  <p className="text-base">{card.shortPhrase}</p>

                  {isRead ? (
                    <p className="text-sm leading-relaxed opacity-90">
                      {card.interpretation}
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={() => readMeaning(key)}
                      className="text-sm underline"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--deck-accent)",
                        cursor: "pointer",
                      }}
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

      {/* «Раскрыть все» appears only after the first flip, and disappears once all are open. */}
      {anyFlipped && !allFlipped && (
        <button
          type="button"
          onClick={revealAll}
          className="mt-8 self-center rounded-full px-6 py-2 text-sm"
          style={{
            background: "color-mix(in srgb, var(--deck-accent) 18%, transparent)",
            border: "1px solid var(--deck-accent)",
            color: "var(--deck-soft)",
            cursor: "pointer",
          }}
        >
          {REVEAL_OPEN_ALL}
        </button>
      )}

      <button
        type="button"
        onClick={() => goTo("result")}
        className="fixed inset-x-0 bottom-0 mx-auto w-full max-w-md px-6 py-4 text-base font-semibold"
        style={{
          background: "var(--deck-accent)",
          color: "var(--deck-bg)",
          border: "none",
          cursor: "pointer",
        }}
      >
        {REVEAL_TO_RESULT}
      </button>
    </main>
  );
}

export default RevealScreen;

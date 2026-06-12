import type { CSSProperties } from "react";
import { stagger } from "motion/react";
import * as m from "motion/react-m";

import { useSelection } from "../../stores/selection";
import { getSafeAreaInsets } from "../../lib/telegram";
import { CardArt } from "../CardArtFallback";
import {
  ORIENTATION_LABELS,
  RESULT_AGAIN_CTA,
  RESULT_GENERAL,
  RESULT_HEADER,
  RESULT_HISTORY_CTA,
  RESULT_LABELS,
  RESULT_SAVE_CTA,
  RESULT_SOON_BADGE,
  SUMMARY_LABELS,
} from "../../reading/copy";
import type { MockReading } from "../../reading/types";

// READ-09 / D-12 — the closing screen. Renders EVERY MockReading field on premium-dark
// glass: header, a meta row (вопрос/тема/колода/расклад/дата), one glass card per drawn
// card, and the summary panel as a staggered "final gather". Sticky actions: «Ещё расклад»
// wired to startReadingAgain (D-04, preserves question+topic); «Сохранить карточку» / «История»
// are honest «скоро» stubs (D-12). The question is rendered as a TEXT node (T-3-01) — no
// dangerouslySetInnerHTML anywhere. FlowRoot already routes step==="result" here (untouched).

// Deterministic DD.MM.YYYY from the ISO date part (no timezone drift, no locale dependency).
function formatDate(iso: string): string {
  const [y, mo, d] = iso.slice(0, 10).split("-");
  return d && mo && y ? `${d}.${mo}.${y}` : iso;
}

const GLASS: CSSProperties = {
  background: "color-mix(in srgb, var(--deck-deep) 70%, transparent)",
  border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
  borderRadius: 16,
};

const summaryContainer = {
  rest: {},
  reveal: { transition: { delayChildren: stagger(0.12) } },
};
const summaryItem = {
  rest: { opacity: 0, y: 8 },
  reveal: { opacity: 1, y: 0 },
};

export function ResultScreen() {
  const reading = useSelection((s) => s.reading);
  const startReadingAgain = useSelection((s) => s.startReadingAgain);
  const insets = getSafeAreaInsets();

  // Reachable only after a reading is built; guard defensively with an element (FlowRoot
  // screen registry is `() => Element`, so never return null).
  if (!reading) {
    return <main className="flex min-h-full items-center justify-center" />;
  }

  const r: MockReading = reading;
  const metaRows: ReadonlyArray<{ label: string; value: string }> = [
    { label: RESULT_LABELS.question, value: r.question ?? RESULT_GENERAL },
    { label: RESULT_LABELS.topic, value: r.topic },
    { label: RESULT_LABELS.deck, value: r.deckSlug },
    { label: RESULT_LABELS.spread, value: r.spreadSlug },
    { label: RESULT_LABELS.date, value: formatDate(r.createdAt) },
  ];

  const summaryRows: ReadonlyArray<{ label: string; value: string }> = [
    { label: SUMMARY_LABELS.linkage, value: r.summary.linkage },
    { label: SUMMARY_LABELS.mainFactor, value: r.summary.mainFactor },
    { label: SUMMARY_LABELS.attention, value: r.summary.attention },
    { label: SUMMARY_LABELS.softAdvice, value: r.summary.softAdvice },
    { label: SUMMARY_LABELS.closingPhrase, value: r.summary.closingPhrase },
  ];

  return (
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-28 pt-8"
      style={{ color: "var(--deck-soft)" }}
    >
      <h1 className="text-3xl font-semibold" style={{ color: "var(--deck-accent)" }}>
        {RESULT_HEADER}
      </h1>

      {/* Meta row — eyebrow Label + value. */}
      <section className="grid gap-3" style={{ ...GLASS, padding: 16 }}>
        {metaRows.map((row) => (
          <div key={row.label} className="flex flex-col">
            <span className="text-xs uppercase tracking-wide opacity-50">{row.label}</span>
            <span className="text-base">{row.value}</span>
          </div>
        ))}
      </section>

      {/* One glass card per drawn card. */}
      <section className="grid gap-5">
        {r.cards.map((card) => (
          <article
            key={`${card.positionTitle}|${card.name}`}
            className="flex flex-col gap-3 p-4"
            style={GLASS}
          >
            <div className="flex items-start gap-4">
              <CardArt src={null} alt={card.name} />
              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide opacity-50">
                  {card.positionTitle}
                </span>
                <h2 className="text-xl font-semibold" style={{ color: "var(--deck-accent)" }}>
                  {card.name}
                </h2>
                <span className="text-xs opacity-60">
                  {ORIENTATION_LABELS[card.orientation]}
                </span>
                <p className="mt-1 text-sm opacity-80">{card.shortMeaning}</p>
              </div>
            </div>
            <p className="text-base leading-relaxed">{card.interpretation}</p>
            <p className="text-sm italic opacity-75">{card.deckAccent}</p>
          </article>
        ))}
      </section>

      {/* Summary panel — the staggered "final gather". */}
      <m.section
        variants={summaryContainer}
        initial="rest"
        animate="reveal"
        className="grid gap-4 p-4"
        style={GLASS}
      >
        {summaryRows.map((row) => (
          <m.div key={row.label} variants={summaryItem} className="flex flex-col">
            <span className="text-xs uppercase tracking-wide opacity-50">{row.label}</span>
            <span className="text-base leading-relaxed">{row.value}</span>
          </m.div>
        ))}
      </m.section>

      {/* Sticky actions — «Ещё расклад» wired (D-04); save/история honest «скоро» stubs (D-12). */}
      <div
        className="fixed inset-x-0 bottom-0 mx-auto flex w-full max-w-md items-center gap-3 px-6 pt-3"
        style={{
          paddingBottom: 12 + insets.bottom,
          background:
            "linear-gradient(to top, var(--deck-bg), color-mix(in srgb, var(--deck-bg) 0%, transparent))",
        }}
      >
        <m.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={startReadingAgain}
          className="flex-1 rounded-full py-3 text-base font-semibold"
          style={{
            background: "var(--deck-accent)",
            color: "var(--deck-bg)",
            border: "none",
            cursor: "pointer",
          }}
        >
          {RESULT_AGAIN_CTA}
        </m.button>
        <button
          type="button"
          disabled
          className="flex flex-col items-center rounded-full px-4 py-2 text-xs opacity-50"
          style={{ background: "transparent", border: "1px solid var(--deck-soft)", color: "inherit" }}
        >
          <span>{RESULT_SAVE_CTA}</span>
          <span className="text-[10px] uppercase tracking-wide">{RESULT_SOON_BADGE}</span>
        </button>
        <button
          type="button"
          disabled
          className="flex flex-col items-center rounded-full px-4 py-2 text-xs opacity-50"
          style={{ background: "transparent", border: "1px solid var(--deck-soft)", color: "inherit" }}
        >
          <span>{RESULT_HISTORY_CTA}</span>
          <span className="text-[10px] uppercase tracking-wide">{RESULT_SOON_BADGE}</span>
        </button>
      </div>
    </main>
  );
}

export default ResultScreen;

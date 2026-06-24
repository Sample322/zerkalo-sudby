import { Fragment } from "react";
import { stagger } from "motion/react";
import * as m from "motion/react-m";

import { useSelection } from "../../stores/selection";
import { useReadingDetail, useReadingsList } from "../../hooks/useReadings";
import { mapReadingOutToMock } from "../../reading/createReading";
import { EASE } from "../../lib/motion";
import { getSafeAreaInsets } from "../../lib/telegram";
import { CardArt } from "../CardArtFallback";
import {
  HISTORY_LOADING,
  NAV_BACK,
  ORIENTATION_LABELS,
  RESULT_AGAIN_CTA,
  RESULT_GENERAL,
  RESULT_HEADER,
  RESULT_HISTORY_CTA,
  RESULT_LABELS,
  SUMMARY_LABELS,
} from "../../reading/copy";
import type { MockReading } from "../../reading/types";

// READ-09 / D-12 — the closing screen, serving TWO modes off the same chrome (D-02):
//   • step === "result"        — the LIVE flow result (reads the ephemeral store `reading`);
//                                sticky «Ещё расклад» / «сохранить» / «история».
//   • step === "readingDetail" — REOPEN of an immutable past reading (HIST-03), mapped through the
//                                SHARED mapper with a gentle fade-in (NO flip replay) + back→History.
// Every value renders as a TEXT node (T-05-XSS) — no dangerouslySetInnerHTML anywhere.

// Deterministic DD.MM.YYYY from the ISO date part (no timezone drift, no locale dependency).
function formatDate(iso: string): string {
  const [y, mo, d] = iso.slice(0, 10).split("-");
  return d && mo && y ? `${d}.${mo}.${y}` : iso;
}

// Staggered "final gather" used for the summary in the live flow, and — in detail mode — for the
// whole card list + summary so a reopen is a soft fade-in, never the flip-reveal.
const fadeContainer = {
  rest: {},
  reveal: { transition: { delayChildren: stagger(0.08) } },
};
const fadeItem = {
  rest: { opacity: 0, y: 8 },
  reveal: { opacity: 1, y: 0 },
};

// The tableau «на столе»: cards drop in with a stagger + a small per-card tilt (custom) so the
// spread reads as physical cards laid on a ritual table, not a flat row.
const tableauContainer = {
  rest: {},
  reveal: { transition: { delayChildren: stagger(0.1) } },
};
const tableauItem = {
  rest: { opacity: 0, y: 18 },
  reveal: (rot: number) => ({ opacity: 1, y: 0, rotate: rot }),
};

/**
 * Read the immutable reading the detail view should render (HIST-03). CONTENT comes from the
 * immutable `GET /api/readings/{id}` body; the meta (question / deck / spread / date) from the
 * tapped history list item in the `["readings","list"]` cache. Null while loading or id absent.
 */
function useDetailReading(): MockReading | null {
  const detailReadingId = useSelection((s) => s.detailReadingId);
  const { data: detail } = useReadingDetail(detailReadingId);
  const { data: list } = useReadingsList();

  if (!detail) return null;

  const item = list?.find((r) => r.reading_id === detailReadingId);
  return mapReadingOutToMock(detail, {
    question: item?.question ?? null,
    topic: "",
    deckSlug: item?.deck_name ?? "",
    spreadSlug: item?.spread_name ?? "",
    createdAt: item?.created_at ?? "",
  });
}

interface ReadingBodyProps {
  reading: MockReading;
  /** Detail mode fades the card list in too (D-02); the live flow keeps cards static. */
  fadeCards: boolean;
}

/** The shared meta + cards + summary body — identical chrome for both modes. */
function ReadingBody({ reading: r, fadeCards }: ReadingBodyProps) {
  const metaRows: ReadonlyArray<{ label: string; value: string }> = [
    { label: RESULT_LABELS.question, value: r.question ?? RESULT_GENERAL },
    { label: RESULT_LABELS.topic, value: r.topic },
    { label: RESULT_LABELS.deck, value: r.deckSlug },
    { label: RESULT_LABELS.spread, value: r.spreadSlug },
    { label: RESULT_LABELS.date, value: formatDate(r.createdAt) },
  ].filter((row) => row.value.trim().length > 0);

  // The first four summary beats render as labelled rows; the closing phrase is the finale.
  const summaryRows: ReadonlyArray<{ label: string; value: string }> = [
    { label: SUMMARY_LABELS.linkage, value: r.summary.linkage },
    { label: SUMMARY_LABELS.mainFactor, value: r.summary.mainFactor },
    { label: SUMMARY_LABELS.attention, value: r.summary.attention },
    { label: SUMMARY_LABELS.softAdvice, value: r.summary.softAdvice },
  ];

  return (
    <>
      {/* Meta — eyebrow label + value on glass. */}
      <section className="panel grid gap-3 p-5">
        {metaRows.map((row) => (
          <div key={row.label} className="flex flex-col gap-0.5">
            <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
              {row.label}
            </span>
            <span className="text-[17px]" style={{ color: "var(--deck-soft)" }}>
              {row.value}
            </span>
          </div>
        ))}
      </section>

      {/* The spread laid out «на столе» — the drawn cards as faces on a felt altar, the visual
          composition of the reading (READ-09). The detailed per-card reading follows below. */}
      <CardTableau cards={r.cards} />

      {/* The per-card reading, woven together by the «нить смысла» (READ-09): a thin glowing thread
          + ✦ node draws between consecutive blocks, so the cards read as one connected message.
          The card faces + positions live in the tableau above; these blocks carry the words. */}
      <m.section
        className="flex flex-col"
        variants={fadeCards ? fadeContainer : undefined}
        initial={fadeCards ? "rest" : undefined}
        animate={fadeCards ? "reveal" : undefined}
      >
        {r.cards.map((card, i) => (
          <Fragment key={`${card.positionTitle}|${card.name}`}>
            {i > 0 && <MeaningThread />}
            <m.article
              className="panel flex flex-col gap-2 p-4"
              variants={fadeCards ? fadeItem : undefined}
            >
              <h2 className="font-display metal-text text-[21px] leading-tight">{card.name}</h2>
              <span className="eyebrow" style={{ color: "var(--color-mist-dim)", letterSpacing: "0.16em" }}>
                {ORIENTATION_LABELS[card.orientation]}
              </span>
              <p className="text-[15px] italic" style={{ color: "color-mix(in srgb, var(--color-mist) 82%, transparent)" }}>
                {card.shortMeaning}
              </p>
              <p className="text-[16.5px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
                {card.interpretation}
              </p>
              <p className="text-[15px] italic" style={{ color: "color-mix(in srgb, var(--deck-glow) 78%, var(--deck-soft))" }}>
                {card.deckAccent}
              </p>
            </m.article>
          </Fragment>
        ))}
      </m.section>

      {/* Итог — the gold-crowned altar; labelled beats then the closing phrase finale. */}
      <m.section variants={fadeContainer} initial="rest" animate="reveal" className="panel-altar relative overflow-hidden p-6">
        <div
          aria-hidden="true"
          className="absolute left-1/2 top-0 h-px w-36 -translate-x-1/2"
          style={{ background: "linear-gradient(90deg, transparent, var(--deck-accent), transparent)" }}
        />
        <m.p variants={fadeItem} className="eyebrow text-center" style={{ letterSpacing: "0.32em" }}>
          Итог
        </m.p>
        <div className="mt-4 grid gap-4">
          {summaryRows.map((row) => (
            <m.div key={row.label} variants={fadeItem} className="flex flex-col gap-0.5">
              <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
                {row.label}
              </span>
              <span className="text-[16.5px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
                {row.value}
              </span>
            </m.div>
          ))}
        </div>
        <m.p
          variants={fadeItem}
          className="font-display mt-6 text-center text-[22px] italic leading-snug"
          style={{ color: "var(--deck-soft)", textShadow: "0 0 24px color-mix(in srgb, var(--deck-glow) 18%, transparent)" }}
        >
          {r.summary.closingPhrase}
        </m.p>
      </m.section>
    </>
  );
}

export function ResultScreen() {
  const step = useSelection((s) => s.step);
  const isDetail = step === "readingDetail";

  const liveReading = useSelection((s) => s.reading);
  const detailReading = useDetailReading();
  const reading = isDetail ? detailReading : liveReading;

  const startReadingAgain = useSelection((s) => s.startReadingAgain);
  const goTo = useSelection((s) => s.goTo);
  const back = useSelection((s) => s.back);
  const insets = getSafeAreaInsets();

  if (isDetail && !reading) {
    return (
      <main className="flex min-h-full flex-col gap-6 px-6 pb-12 pt-8" style={{ color: "var(--deck-soft)" }}>
        <DetailHeader onBack={back} />
        <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
          {HISTORY_LOADING}
        </p>
      </main>
    );
  }

  if (!reading) {
    return <main className="flex min-h-full items-center justify-center" />;
  }

  // ---- Detail mode (HIST-03): immutable reopen, fade-in, back → History, no live CTAs. ----
  if (isDetail) {
    return (
      <main className="flex min-h-full flex-col gap-6 px-6 pb-12 pt-8" style={{ color: "var(--deck-soft)" }}>
        <DetailHeader onBack={back} />
        <ReadingBody reading={reading} fadeCards />
      </main>
    );
  }

  // ---- Live result mode (READ-09 / D-12). ----
  return (
    <main className="flex min-h-full flex-col gap-6 px-6 pb-48 pt-9" style={{ color: "var(--deck-soft)" }}>
      <header className="flex flex-col items-center gap-3 text-center">
        <span className="eyebrow">Зеркало Судьбы</span>
        <h1 className="font-display metal-text text-[34px] leading-tight">{RESULT_HEADER}</h1>
        <div className="flex items-center gap-3">
          <span className="gold-rule" style={{ width: 70 }} />
          <span style={{ color: "var(--deck-accent)", fontSize: 13 }}>✦</span>
          <span className="gold-rule" style={{ width: 70 }} />
        </div>
      </header>

      <ReadingBody reading={reading} fadeCards={false} />

      {/* Sticky actions — «Ещё расклад» (D-04) + «История» (D-10) as stacked full-width pills for
          comfortable mobile tap targets. The reading is already saved to history, so the Phase-7
          «сохранить» stub is intentionally omitted (a dead control only added clutter). */}
      <div
        className="fixed inset-x-0 bottom-0 z-20 mx-auto flex w-full max-w-md flex-col gap-2.5 px-6 pt-3"
        style={{
          paddingBottom: 14 + insets.bottom,
          background: "linear-gradient(to top, var(--deck-bg) 72%, var(--deck-bg) 40%, transparent)",
        }}
      >
        <m.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={startReadingAgain}
          className="pill-primary w-full py-4 text-[18px] outline-none focus-visible:ring-2"
        >
          {RESULT_AGAIN_CTA}
        </m.button>
        <m.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={() => goTo("history")}
          className="pill-ghost w-full py-3 text-[15px] outline-none focus-visible:ring-2"
        >
          {RESULT_HISTORY_CTA}
        </m.button>
      </div>
    </main>
  );
}

/**
 * «Итог на столе» — the drawn cards laid as faces on a felt altar (READ-09). Each card drops in
 * with a slight per-card tilt so the spread reads as a physical layout on a ritual table, with the
 * position label beneath; the detailed words live in the reading blocks below. Compositor-only.
 */
function CardTableau({ cards }: { cards: MockReading["cards"] }) {
  const mid = (cards.length - 1) / 2;
  const faceWidth = cards.length > 3 ? 74 : 94;
  return (
    <m.section
      className="panel-altar relative flex flex-wrap items-end justify-center gap-3 overflow-hidden px-4 py-6"
      variants={tableauContainer}
      initial="rest"
      animate="reveal"
    >
      {/* Gold crown hairline (mirrors the summary altar). */}
      <div
        aria-hidden="true"
        className="absolute left-1/2 top-0 h-px w-32 -translate-x-1/2"
        style={{ background: "linear-gradient(90deg, transparent, var(--deck-accent), transparent)" }}
      />
      {/* The table line the cards rest upon. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-8"
        style={{
          bottom: 50,
          height: 1,
          background:
            "linear-gradient(90deg, transparent, color-mix(in srgb, var(--deck-accent) 40%, transparent), transparent)",
        }}
      />
      {cards.map((card, i) => (
        <m.div
          key={`${card.positionTitle}|${card.name}`}
          custom={(i - mid) * 3}
          variants={tableauItem}
          transition={{ duration: 0.6, ease: EASE.softOut }}
          className="relative z-10 flex flex-col items-center gap-2"
          style={{ transformOrigin: "bottom center" }}
        >
          <CardArt src={null} alt={card.positionTitle} glyph={card.name.charAt(0)} width={faceWidth} />
          <span className="eyebrow max-w-[7rem] text-center" style={{ color: "var(--color-mist-dim)" }}>
            {card.positionTitle}
          </span>
        </m.div>
      ))}
    </m.section>
  );
}

/**
 * «Нить смысла» — a thin glowing thread + ✦ node that links one card to the next (READ-09). The
 * line draws downward (scaleY from the top) and the node blooms in; compositor-only and driven by
 * its own `animate` (independent of the card fade), so it reveals in both the live and the
 * reopened-detail views. Decorative → aria-hidden.
 */
function MeaningThread() {
  return (
    <div aria-hidden="true" className="relative mx-auto flex h-11 w-px items-center justify-center">
      <m.span
        className="absolute inset-0"
        style={{
          transformOrigin: "top",
          background:
            "linear-gradient(to bottom, transparent, color-mix(in srgb, var(--deck-accent) 65%, transparent), transparent)",
        }}
        initial={{ scaleY: 0, opacity: 0 }}
        animate={{ scaleY: 1, opacity: 1 }}
        transition={{ duration: 0.55, ease: EASE.softOut }}
      />
      <m.span
        className="relative font-display"
        style={{
          fontSize: 12,
          color: "var(--deck-accent)",
          textShadow: "0 0 12px color-mix(in srgb, var(--deck-glow) 75%, transparent)",
        }}
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 0.92, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.18, ease: EASE.softOut }}
      >
        ✦
      </m.span>
    </div>
  );
}

/** Detail-mode header — back→History affordance + title (D-11). */
function DetailHeader({ onBack }: { onBack: () => void }) {
  return (
    <header className="flex items-center gap-3 pt-1">
      <m.button
        type="button"
        whileTap={{ scale: 0.94 }}
        onClick={onBack}
        aria-label={NAV_BACK}
        className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-[18px] outline-none focus-visible:ring-2"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
          color: "var(--deck-accent)",
          cursor: "pointer",
        }}
      >
        <span aria-hidden="true">←</span>
      </m.button>
      <h1 className="font-display metal-text text-[28px] leading-tight">{RESULT_HEADER}</h1>
    </header>
  );
}

export default ResultScreen;

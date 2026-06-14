import type { CSSProperties } from "react";
import { stagger } from "motion/react";
import * as m from "motion/react-m";

import { useSelection } from "../../stores/selection";
import { useReadingDetail, useReadingsList } from "../../hooks/useReadings";
import { mapReadingOutToMock } from "../../reading/createReading";
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
  RESULT_SAVE_CTA,
  RESULT_SOON_BADGE,
  SUMMARY_LABELS,
} from "../../reading/copy";
import type { MockReading } from "../../reading/types";

// READ-09 / D-12 — the closing screen, now serving TWO modes off the same chrome (D-02):
//   • step === "result"        — the LIVE flow result (reads the ephemeral store `reading`);
//                                sticky actions «Ещё расклад» / «сохранить» / «история».
//   • step === "readingDetail" — REOPEN of an immutable past reading (HIST-03). Reads the
//                                reading fetched by id (`useReadingDetail`), mapped through the
//                                SHARED ReadingOut→MockReading mapper, with the gentle opacity
//                                fade-in (NO flip/reveal replay, D-02) and a single back→History
//                                affordance — NONE of the live-flow CTAs (D-11).
// The question/values render as TEXT nodes (T-05-XSS) — no dangerouslySetInnerHTML anywhere.

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

// The opacity-stagger used for the summary "final gather" in the live flow, and — in detail
// mode — for the whole card list + summary so a reopen is a soft fade-in, never the flip-reveal.
const fadeContainer = {
  rest: {},
  reveal: { transition: { delayChildren: stagger(0.08) } },
};
const fadeItem = {
  rest: { opacity: 0, y: 8 },
  reveal: { opacity: 1, y: 0 },
};

/**
 * Read the immutable reading the detail view should render (HIST-03). The per-card + summary
 * CONTENT comes from the immutable `GET /api/readings/{id}` body; the meta (question / deck /
 * spread / date) is sourced from the tapped history list item in the `["readings","list"]`
 * cache so the displayed meta stays consistent with the list (the §14.5 body omits those).
 * Returns `null` while the detail is still loading (or the id is missing).
 */
function useDetailReading(): MockReading | null {
  const detailReadingId = useSelection((s) => s.detailReadingId);
  const { data: detail } = useReadingDetail(detailReadingId);
  const { data: list } = useReadingsList();

  if (!detail) return null;

  const item = list?.find((r) => r.reading_id === detailReadingId);
  return mapReadingOutToMock(detail, {
    question: item?.question ?? null,
    // The light list item carries human deck/spread titles (not slugs) — show those; `topic`
    // is not part of either source, so it stays empty and its meta row is skipped.
    topic: "",
    deckSlug: item?.deck_name ?? "",
    spreadSlug: item?.spread_name ?? "",
    // Empty when the list item is absent → the date meta row is skipped (never show a raw id).
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

  const summaryRows: ReadonlyArray<{ label: string; value: string }> = [
    { label: SUMMARY_LABELS.linkage, value: r.summary.linkage },
    { label: SUMMARY_LABELS.mainFactor, value: r.summary.mainFactor },
    { label: SUMMARY_LABELS.attention, value: r.summary.attention },
    { label: SUMMARY_LABELS.softAdvice, value: r.summary.softAdvice },
    { label: SUMMARY_LABELS.closingPhrase, value: r.summary.closingPhrase },
  ];

  return (
    <>
      {/* Meta row — eyebrow Label + value. */}
      <section className="grid gap-3" style={{ ...GLASS, padding: 16 }}>
        {metaRows.map((row) => (
          <div key={row.label} className="flex flex-col">
            <span className="text-xs uppercase tracking-wide opacity-50">{row.label}</span>
            <span className="text-base">{row.value}</span>
          </div>
        ))}
      </section>

      {/* One glass card per drawn card — in detail mode each card softly fades in (D-02). */}
      <m.section
        className="grid gap-5"
        variants={fadeCards ? fadeContainer : undefined}
        initial={fadeCards ? "rest" : undefined}
        animate={fadeCards ? "reveal" : undefined}
      >
        {r.cards.map((card) => (
          <m.article
            key={`${card.positionTitle}|${card.name}`}
            className="flex flex-col gap-3 p-4"
            style={GLASS}
            variants={fadeCards ? fadeItem : undefined}
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
          </m.article>
        ))}
      </m.section>

      {/* Summary panel — the staggered "final gather" (shared by both modes). */}
      <m.section
        variants={fadeContainer}
        initial="rest"
        animate="reveal"
        className="grid gap-4 p-4"
        style={GLASS}
      >
        {summaryRows.map((row) => (
          <m.div key={row.label} variants={fadeItem} className="flex flex-col">
            <span className="text-xs uppercase tracking-wide opacity-50">{row.label}</span>
            <span className="text-base leading-relaxed">{row.value}</span>
          </m.div>
        ))}
      </m.section>
    </>
  );
}

export function ResultScreen() {
  const step = useSelection((s) => s.step);
  const isDetail = step === "readingDetail";

  // Both hooks run every render (no conditional hooks); `useDetailReading` is gated on the
  // detail id internally and is a no-op fetch in live mode (id is null).
  const liveReading = useSelection((s) => s.reading);
  const detailReading = useDetailReading();
  const reading = isDetail ? detailReading : liveReading;

  const startReadingAgain = useSelection((s) => s.startReadingAgain);
  const goTo = useSelection((s) => s.goTo);
  const back = useSelection((s) => s.back);
  const insets = getSafeAreaInsets();

  // Detail mode: show a soft loading line while the immutable reading is in flight (HIST-03).
  if (isDetail && !reading) {
    return (
      <main
        className="flex min-h-full flex-col gap-6 px-6 pb-12 pt-8"
        style={{ color: "var(--deck-soft)" }}
      >
        <DetailHeader onBack={back} />
        <p className="px-1 opacity-70">{HISTORY_LOADING}</p>
      </main>
    );
  }

  // Reachable only after a reading exists; guard defensively with an element (FlowRoot
  // screen registry is `() => Element`, so never return null).
  if (!reading) {
    return <main className="flex min-h-full items-center justify-center" />;
  }

  // ---- Detail mode (HIST-03): immutable reopen, fade-in, back → History, no live CTAs. ----
  if (isDetail) {
    return (
      <main
        className="flex min-h-full flex-col gap-6 px-6 pb-12 pt-8"
        style={{ color: "var(--deck-soft)" }}
      >
        <DetailHeader onBack={back} />
        <ReadingBody reading={reading} fadeCards />
      </main>
    );
  }

  // ---- Live result mode (READ-09 / D-12): unchanged sticky actions. ----
  return (
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-28 pt-8"
      style={{ color: "var(--deck-soft)" }}
    >
      <h1 className="text-3xl font-semibold" style={{ color: "var(--deck-accent)" }}>
        {RESULT_HEADER}
      </h1>

      <ReadingBody reading={reading} fadeCards={false} />

      {/* Sticky actions — «Ещё расклад» wired (D-04); save «скоро» stub; «История» → list (D-10). */}
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
        {/* «История» un-stubbed (D-10) → routes to the History list. */}
        <m.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={() => goTo("history")}
          className="flex flex-col items-center rounded-full px-4 py-2 text-xs outline-none focus-visible:ring-2"
          style={{
            background: "transparent",
            border: "1px solid var(--deck-soft)",
            color: "inherit",
            cursor: "pointer",
          }}
        >
          <span>{RESULT_HISTORY_CTA}</span>
        </m.button>
      </div>
    </main>
  );
}

/** Detail-mode header — title + a single back→History affordance (D-11). */
function DetailHeader({ onBack }: { onBack: () => void }) {
  return (
    <header className="flex items-center gap-3">
      <m.button
        type="button"
        whileTap={{ scale: 0.94 }}
        onClick={onBack}
        aria-label={NAV_BACK}
        className="grid h-10 w-10 shrink-0 place-items-center rounded-full outline-none focus-visible:ring-2"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 60%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
          color: "var(--deck-accent)",
          cursor: "pointer",
        }}
      >
        <span aria-hidden="true">←</span>
      </m.button>
      <h1 className="text-3xl font-semibold" style={{ color: "var(--deck-accent)" }}>
        {RESULT_HEADER}
      </h1>
    </header>
  );
}

export default ResultScreen;

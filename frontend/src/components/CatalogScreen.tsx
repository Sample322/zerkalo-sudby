import { useState } from "react";
import * as m from "motion/react-m";

import { useDecks } from "../hooks/useDecks";
import { useMe } from "../hooks/useMe";
import { useRecommendation, useSpreads } from "../hooks/useSpreads";
import { getContentSafeAreaInsets, getSafeAreaInsets } from "../lib/telegram";
import { createReading, ReadingError } from "../reading/createReading";
import { formatRemaining } from "../reading/limitCopy";
import {
  HISTORY_HEADER,
  LIMIT_LAST_ONE_HINT,
  PROFILE_HEADER,
  QUESTION_EMPTY_HELPER,
  QUESTION_PLACEHOLDER,
  QUESTION_TOO_SHORT_HINT,
  READING_CHANGE_DECK,
  READING_ERROR,
  READING_RETRY,
  START_CTA,
  START_GATE_HINT,
} from "../reading/copy";
import { canStart, questionValidity, useSelection } from "../stores/selection";
import { useDeckTheme } from "../theme/useDeckTheme";
import { DeckCarousel } from "./DeckCarousel";
import { PaywallSheet } from "./PaywallSheet";
import { SpreadCard } from "./SpreadCard";
import { ThrottleToast } from "./ThrottleToast";
import { TopicChip } from "./TopicChip";

/** 7 days in milliseconds — the pre-emptive paywall reset moment is `week_start + 7d` (06-02). */
const WEEK_MS = 7 * 86_400_000;

/**
 * The reset moment for the pre-emptive paywall (when freeLeft===0 is known from `useMe` BEFORE
 * any POST): `week_start + 7d`, mirroring the backend `_compute_reset_at`. On the belt-and-
 * suspenders catch path the authoritative `reset_at` rides on the ReadingError instead. Returns
 * null when no window is anchored yet (the sheet then shows the «совсем скоро» fallback).
 */
function computeResetAt(weekStart: string | null | undefined): string | null {
  if (!weekStart) return null;
  const anchored = new Date(weekStart);
  if (Number.isNaN(anchored.getTime())) return null;
  return new Date(anchored.getTime() + WEEK_MS).toISOString();
}

// The 7 MVP topics (REQUIREMENTS HOME-03) — slug -> RU label.
const TOPICS: { slug: string; label: string }[] = [
  { slug: "love", label: "Любовь" },
  { slug: "work", label: "Работа" },
  { slug: "money", label: "Деньги" },
  { slug: "choice", label: "Выбор" },
  { slug: "day", label: "День" },
  { slug: "self_reflection", label: "Саморефлексия" },
  { slug: "general", label: "Общий вопрос" },
];

// The catalog browsing surface: topics + decks + spreads + a topic recommendation, wired to
// the selection store and live per-deck theming. Server state stays in TanStack Query; this
// screen only reads it.
export function CatalogScreen() {
  useDeckTheme(); // selecting a deck re-themes the whole surface (UI-02)

  const topic = useSelection((s) => s.topic);
  const deckSlug = useSelection((s) => s.deckSlug);
  const spreadSlug = useSelection((s) => s.spreadSlug);
  const question = useSelection((s) => s.question);
  const localReversals = useSelection((s) => s.reversalsEnabled);
  const setTopic = useSelection((s) => s.setTopic);
  const setDeck = useSelection((s) => s.setDeck);
  const setSpread = useSelection((s) => s.setSpread);
  const setQuestion = useSelection((s) => s.setQuestion);
  const setReading = useSelection((s) => s.setReading);
  const goTo = useSelection((s) => s.goTo);

  const decksQuery = useDecks();
  const spreadsQuery = useSpreads(topic, deckSlug);
  const recommendation = useRecommendation(topic, deckSlug);

  // D-09 reversals source: prefer the persisted `GET /api/me` flag; fall back to the local
  // toggle only until the profile query resolves (so the CTA is never blocked on the network).
  const meQuery = useMe();
  const reversalsEnabled = meQuery.data?.settings.reversals_enabled ?? localReversals;

  // D-09/D-10 free-limit display chrome (non-authoritative — the server gate is the real arbiter,
  // T-06-14). `freeLeft` is undefined while `useMe` is pending or limits are absent.
  const limits = meQuery.data?.limits;
  const freeLeft = limits
    ? Math.max(0, limits.free_weekly_limit - limits.free_used_this_week)
    : undefined;

  // HOME-07 start gate (topic + deck + spread all chosen) — the pure store helper.
  const ready = canStart({ topic, deckSlug, spreadSlug });
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState(false);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paywallResetAt, setPaywallResetAt] = useState<string | null>(null);
  const [throttleOpen, setThrottleOpen] = useState(false);

  const selectedSpread = spreadsQuery.data?.find((s) => s.slug === spreadSlug);

  async function handleStart() {
    if (!ready || isStarting || !selectedSpread || !topic || !deckSlug || !spreadSlug) {
      return;
    }
    // D-03 pre-emptive paywall: known-exhausted quota opens the sheet instead of a wasted POST.
    if (freeLeft === 0) {
      setPaywallResetAt(computeResetAt(limits?.week_start));
      setPaywallOpen(true);
      return;
    }
    setIsStarting(true);
    setStartError(false);
    try {
      // THE single Phase-4 boundary (D-05): build the MockReading via the seam, write it to the
      // store `reading` slot BEFORE goTo("ritual") so the downstream slot is populated on paint.
      const reading = await createReading({
        question: question.trim().length === 0 ? null : question, // D-13: empty => general
        topic,
        deckSlug,
        spreadSlug,
        reversalsEnabled,
        positions: selectedSpread.positions,
      });
      setReading(reading);
      goTo("ritual");
    } catch (err) {
      // D-08: route the ONE catch by the discriminated ReadingError.kind to three DISTINCT
      // surfaces. The reading was NOT started and the limit NOT consumed on any branch.
      if (err instanceof ReadingError && err.kind === "throttle") {
        setThrottleOpen(true);
      } else if (err instanceof ReadingError && err.kind === "paywall") {
        setPaywallResetAt(err.resetAt ?? null);
        setPaywallOpen(true);
      } else {
        setStartError(true);
      }
      setIsStarting(false);
    }
  }

  // D-08 «Сменить колоду»: dismiss the failure panel, keep question + selections (D-04).
  function handleChangeDeck() {
    setStartError(false);
  }

  // D-13 question hint: empty -> neutral optional helper; 1–9 -> soft "уточни"; >=10 -> nothing.
  const isEmptyQuestion = question.trim().length === 0;
  const questionHint = isEmptyQuestion
    ? QUESTION_EMPTY_HELPER
    : questionValidity(question).status === "tooShort"
      ? QUESTION_TOO_SHORT_HINT
      : null;

  return (
    <main className="flex flex-1 flex-col gap-7 px-5 pb-28">
      {/* Header — brand wordmark + the only nav chrome (History / Profile). The ritual/reveal/
          result screens stay chrome-free. */}
      <header className="flex items-center justify-between gap-3 pt-6">
        <div className="flex flex-col">
          <span className="eyebrow">Зеркало Судьбы</span>
          <span className="font-display metal-text text-[26px] leading-tight">Задай вопрос</span>
        </div>
        <nav aria-label="Навигация" className="flex items-center gap-2">
          <NavButton label={HISTORY_HEADER} glyph="⟲" onClick={() => goTo("history")} />
          <NavButton label={PROFILE_HEADER} glyph="☾" onClick={() => goTo("profile")} />
        </nav>
      </header>

      <section aria-label="Вопрос" className="flex flex-col gap-2.5">
        <label htmlFor="reading-question" className="eyebrow px-1">
          Вопрос
        </label>
        {/* HOME-01/02/D-13 — the single untrusted input (threat T-3-01). Controlled value; text
            is only ever a React text node (no raw-HTML sinks). The store clamps to QUESTION_MAX. */}
        <textarea
          id="reading-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={QUESTION_PLACEHOLDER}
          rows={3}
          className="panel w-full resize-none p-4 text-[18px] italic leading-relaxed outline-none placeholder:not-italic focus-visible:ring-2"
          style={{ color: "var(--deck-soft)" }}
        />
        {questionHint && (
          <p className="px-1 text-[15px]" style={{ color: "var(--color-mist-dim)" }}>
            {questionHint}
          </p>
        )}
      </section>

      <section aria-label="Темы" className="flex flex-col gap-3">
        <h2 className="eyebrow px-1">Тема</h2>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {TOPICS.map((t) => (
            <TopicChip
              key={t.slug}
              topic={t.slug}
              label={t.label}
              active={topic === t.slug}
              onSelect={setTopic}
            />
          ))}
        </div>
      </section>

      {recommendation.data && (
        <m.section
          aria-label="Рекомендация"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="panel-altar relative overflow-hidden p-5"
        >
          <div
            aria-hidden="true"
            className="absolute left-1/2 top-0 h-px w-32 -translate-x-1/2"
            style={{ background: "linear-gradient(90deg, transparent, var(--deck-accent), transparent)" }}
          />
          <p className="eyebrow">Колода советует</p>
          <p className="font-display mt-1.5 text-[22px]" style={{ color: "var(--deck-soft)" }}>
            {recommendation.data.recommended_spread.title}
          </p>
          <p className="mt-1.5 text-[16px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
            {recommendation.data.reason}
          </p>
        </m.section>
      )}

      <section aria-label="Колоды" className="flex flex-col gap-3">
        <h2 className="eyebrow px-1">Колоды</h2>
        {decksQuery.isPending ? (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Колода раскладывается…
          </p>
        ) : decksQuery.isError ? (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Колода сейчас молчит. Загляни чуть позже.
          </p>
        ) : decksQuery.data && decksQuery.data.length > 0 ? (
          <DeckCarousel decks={decksQuery.data} selectedSlug={deckSlug} onSelect={setDeck} />
        ) : (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Колоды ещё в тишине.
          </p>
        )}
      </section>

      <section aria-label="Расклады" className="flex flex-col gap-3">
        <h2 className="eyebrow px-1">Расклады</h2>
        {spreadsQuery.isPending ? (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Расклады собираются…
          </p>
        ) : spreadsQuery.isError ? (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Расклады не отозвались. Попробуй позже.
          </p>
        ) : spreadsQuery.data && spreadsQuery.data.length > 0 ? (
          <div className="flex flex-col gap-3">
            {spreadsQuery.data.map((s) => (
              <div
                key={s.slug}
                className="rounded-[18px]"
                style={
                  spreadSlug === s.slug
                    ? {
                        boxShadow:
                          "0 0 0 1.5px var(--deck-accent), 0 0 26px -8px color-mix(in srgb, var(--deck-glow) 75%, transparent)",
                      }
                    : undefined
                }
              >
                <SpreadCard
                  spread={s}
                  recommended={recommendation.data?.recommended_spread.slug === s.slug}
                  onSelect={setSpread}
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>
            Здесь пока пусто.
          </p>
        )}
      </section>

      {/* Sticky «Начать расклад» CTA (HOME-07 / UI-01 / UI-04). Bottom padding from the Telegram
          safe-area insets (NOT env()/100vh). Keyboard-safe via the stable-viewport var. */}
      <div
        className="fixed inset-x-0 bottom-0 z-20 mx-auto w-full max-w-md px-5 pt-3"
        style={{
          paddingBottom:
            16 + Math.max(getSafeAreaInsets().bottom, getContentSafeAreaInsets().bottom),
          background: "linear-gradient(to top, var(--deck-bg) 62%, transparent)",
          maxHeight: "var(--tg-viewport-stable-height, 100dvh)",
        }}
      >
        {!startError && limits && freeLeft !== undefined && freeLeft > 0 && (
          <div className="pb-2">
            <p className="px-1 text-center text-[15px]" style={{ color: "var(--color-mist-dim)" }}>
              {formatRemaining(freeLeft, limits.free_weekly_limit)}
            </p>
            {freeLeft === 1 && (
              <p className="px-1 text-center text-[15px]" style={{ color: "var(--deck-accent)" }}>
                {LIMIT_LAST_ONE_HINT}
              </p>
            )}
          </div>
        )}
        {!ready && !startError && (
          <p className="px-1 pb-2 text-center text-[15px]" style={{ color: "var(--color-mist-dim)" }}>
            {START_GATE_HINT}
          </p>
        )}
        {startError ? (
          <div className="flex flex-col gap-3">
            <p className="px-1 text-center text-[16px] italic" style={{ color: "var(--deck-soft)" }}>
              {READING_ERROR}
            </p>
            <div className="flex gap-3">
              <m.button
                type="button"
                whileTap={{ scale: 0.97 }}
                disabled={isStarting}
                onClick={handleStart}
                aria-disabled={isStarting}
                className="pill-primary flex-1 px-4 py-4 text-[17px] outline-none transition-opacity focus-visible:ring-2 disabled:opacity-50"
              >
                {READING_RETRY}
              </m.button>
              <m.button
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={handleChangeDeck}
                className="pill-ghost flex-1 px-4 py-4 text-[17px] outline-none focus-visible:ring-2"
              >
                {READING_CHANGE_DECK}
              </m.button>
            </div>
          </div>
        ) : (
          <m.button
            type="button"
            whileTap={{ scale: 0.97 }}
            disabled={!ready || isStarting}
            onClick={handleStart}
            aria-disabled={!ready || isStarting}
            className="pill-primary w-full px-4 py-4 text-[18px] outline-none transition-all focus-visible:ring-2 disabled:opacity-40"
            style={ready ? undefined : { boxShadow: "none", filter: "saturate(0.6)" }}
          >
            {START_CTA}
          </m.button>
        )}
      </div>

      <PaywallSheet open={paywallOpen} resetAt={paywallResetAt} onDismiss={() => setPaywallOpen(false)} />
      <ThrottleToast open={throttleOpen} onDismiss={() => setThrottleOpen(false)} />
    </main>
  );
}

/** A refined glass circle for the History / Profile entry points. */
function NavButton({ label, glyph, onClick }: { label: string; glyph: string; onClick: () => void }) {
  return (
    <m.button
      type="button"
      whileTap={{ scale: 0.92 }}
      onClick={onClick}
      aria-label={label}
      title={label}
      className="grid h-11 w-11 place-items-center rounded-full text-[19px] outline-none focus-visible:ring-2"
      style={{
        background: "color-mix(in srgb, var(--deck-deep) 50%, transparent)",
        border: "1px solid color-mix(in srgb, var(--deck-accent) 26%, transparent)",
        color: "var(--deck-accent)",
        cursor: "pointer",
      }}
    >
      <span aria-hidden="true">{glyph}</span>
    </m.button>
  );
}

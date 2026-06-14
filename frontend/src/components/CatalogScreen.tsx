import { useState } from "react";
import * as m from "motion/react-m";

import { useDecks } from "../hooks/useDecks";
import { useMe } from "../hooks/useMe";
import { useRecommendation, useSpreads } from "../hooks/useSpreads";
import { getContentSafeAreaInsets, getSafeAreaInsets } from "../lib/telegram";
import { createReading } from "../reading/createReading";
import {
  HISTORY_HEADER,
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
import { SpreadCard } from "./SpreadCard";
import { TopicChip } from "./TopicChip";

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
// screen only reads it. The "Начать расклад" ritual is Phase 3 (not built here).
export function CatalogScreen() {
  useDeckTheme(); // selecting a deck re-themes the whole surface (UI-02)

  const topic = useSelection((s) => s.topic);
  const deckSlug = useSelection((s) => s.deckSlug);
  const spreadSlug = useSelection((s) => s.spreadSlug);
  const question = useSelection((s) => s.question);
  // D-09: a new reading's reversals are sourced from the PERSISTED user setting
  // (`GET /api/me` settings.reversals_enabled), not the Phase-3 local Zustand toggle. The
  // backend also enforces this (05-04 overrides the request flag from the persisted value), but
  // the client sends the persisted value for consistency. Until `useMe` resolves, fall back to
  // the local toggle so the CTA never blocks. The local toggle stays in the store (harmless now
  // that the persisted flag is authoritative).
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
  const reversalsEnabled =
    meQuery.data?.settings.reversals_enabled ?? localReversals;

  // HOME-07 start gate (topic + deck + spread all chosen) — the pure store helper, never
  // re-implemented here. A pending flag debounces double-taps while the seam resolves; an
  // error flag surfaces the soft in-character failure copy (the Phase-4 swap inherits this).
  const ready = canStart({ topic, deckSlug, spreadSlug });
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState(false);

  // The chosen spread's positions (from the trusted Phase-2 spreads query) are what
  // createReading draws against — passed through, never mirrored into client state.
  const selectedSpread = spreadsQuery.data?.find((s) => s.slug === spreadSlug);

  async function handleStart() {
    // Guard: the CTA is disabled when !ready, but re-check (and ignore re-entrancy / a
    // missing spread record) so the handler is robust to races.
    if (!ready || isStarting || !selectedSpread || !topic || !deckSlug || !spreadSlug) {
      return;
    }
    setIsStarting(true);
    setStartError(false);
    try {
      // THE single Phase-4 boundary (D-05). Build the MockReading via the seam, then write
      // it to the store `reading` slot via setReading — this is the REQUIRED hand-off the
      // ritual/reveal/result steps (03-04/05/06) read. setReading MUST run BEFORE
      // goTo("ritual") so the downstream slot is populated on first paint. The reading is
      // NEVER held in component state and NEVER in TanStack Query (D-05 architecture guard).
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
    } catch {
      // D-08: a failed generation surfaces the soft §9.8 «Колода замолчала…» copy and does
      // NOT advance the step. The recovery affordances (Повторить / Сменить колоду) render in
      // the sticky band below. The limit was NOT consumed server-side (D-09), so Повторить —
      // which simply re-invokes handleStart with the unchanged store params — is free.
      setStartError(true);
      setIsStarting(false);
    }
  }

  // D-08 «Сменить колоду»: dismiss the failure panel and return to the live selection screen
  // with the question + selections PRESERVED (D-04 — never clear `question`). We are already
  // on the selection step, so the user is free to tap a different deck in the carousel.
  function handleChangeDeck() {
    setStartError(false);
  }

  // D-13 question hint, derived from the store's pure validity helper (never re-implemented):
  // empty -> a neutral optional helper (NOT an error, HOME-02); 1–9 -> a soft "уточни" hint
  // (HOME-01); >=10 -> nothing. The hint is a Label line and never blocks the ritual.
  const isEmptyQuestion = question.trim().length === 0;
  const questionHint = isEmptyQuestion
    ? QUESTION_EMPTY_HELPER
    : questionValidity(question).status === "tooShort"
      ? QUESTION_TOO_SHORT_HINT
      : null;

  return (
    <main
      className="flex flex-1 flex-col gap-6 px-4 pb-24"
      style={{ background: "var(--deck-bg)" }}
    >
      {/*
        Atmospheric header row (D-10 / TZ §9.2) — the ONLY navigation chrome. History + Profile
        icon entry points, small + accent-tinted so the immersive feel is preserved. The
        ritual/reveal/result screens stay chrome-free (NO bottom tab bar). The result-screen
        «история» action (un-stubbed below) also routes to History.
      */}
      <nav
        aria-label="Навигация"
        className="flex items-center justify-end gap-2 pt-2"
      >
        <m.button
          type="button"
          whileTap={{ scale: 0.92 }}
          onClick={() => goTo("history")}
          aria-label={HISTORY_HEADER}
          title={HISTORY_HEADER}
          className="grid h-10 w-10 place-items-center rounded-full text-lg outline-none focus-visible:ring-2"
          style={{
            background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
            color: "var(--deck-accent)",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true">🕮</span>
        </m.button>
        <m.button
          type="button"
          whileTap={{ scale: 0.92 }}
          onClick={() => goTo("profile")}
          aria-label={PROFILE_HEADER}
          title={PROFILE_HEADER}
          className="grid h-10 w-10 place-items-center rounded-full text-lg outline-none focus-visible:ring-2"
          style={{
            background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
            color: "var(--deck-accent)",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true">☾</span>
        </m.button>
      </nav>

      <section aria-label="Вопрос" className="flex flex-col gap-2">
        <label
          htmlFor="reading-question"
          className="px-1 text-sm uppercase tracking-wide opacity-70"
        >
          Вопрос
        </label>
        {/*
          HOME-01/02/D-13 — the single untrusted input this phase (threat T-3-01). Bound to
          the store `question` via setQuestion as a CONTROLLED React value; the text is only
          ever a React text node (raw-HTML injection sinks are deliberately never used here).
          The store clamps to QUESTION_MAX, so the value can't exceed the upper bound.
        */}
        <textarea
          id="reading-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={QUESTION_PLACEHOLDER}
          rows={3}
          className="w-full resize-none rounded-2xl border p-4 text-base leading-relaxed outline-none focus-visible:ring-2"
          style={{
            color: "var(--deck-soft)",
            background:
              "linear-gradient(155deg, color-mix(in srgb, var(--deck-bg) 88%, transparent), color-mix(in srgb, var(--deck-deep) 72%, transparent))",
            borderColor: "color-mix(in srgb, var(--deck-soft) 22%, transparent)",
          }}
        />
        {questionHint && (
          <p className="px-1 text-sm opacity-70">{questionHint}</p>
        )}
      </section>

      <section aria-label="Темы">
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
        <section
          aria-label="Рекомендация"
          className="rounded-2xl border p-4"
          style={{
            borderColor: "var(--deck-accent)",
            background: "color-mix(in srgb, var(--deck-accent) 10%, transparent)",
          }}
        >
          <p className="text-xs uppercase tracking-wide opacity-70">Колода советует</p>
          <p className="text-lg font-semibold" style={{ color: "var(--deck-soft)" }}>
            {recommendation.data.recommended_spread.title}
          </p>
          <p className="mt-1 text-sm opacity-80">{recommendation.data.reason}</p>
        </section>
      )}

      <section aria-label="Колоды" className="flex flex-col gap-3">
        <h2 className="px-1 text-sm uppercase tracking-wide opacity-70">Колоды</h2>
        {decksQuery.isPending ? (
          <p className="px-1 opacity-70">Колода раскладывается…</p>
        ) : decksQuery.isError ? (
          <p className="px-1 opacity-70">Колода сейчас молчит. Загляни чуть позже.</p>
        ) : decksQuery.data && decksQuery.data.length > 0 ? (
          <DeckCarousel
            decks={decksQuery.data}
            selectedSlug={deckSlug}
            onSelect={setDeck}
          />
        ) : (
          <p className="px-1 opacity-60">Колоды ещё в тишине.</p>
        )}
      </section>

      <section aria-label="Расклады" className="flex flex-col gap-3">
        <h2 className="px-1 text-sm uppercase tracking-wide opacity-70">Расклады</h2>
        {spreadsQuery.isPending ? (
          <p className="px-1 opacity-70">Расклады собираются…</p>
        ) : spreadsQuery.isError ? (
          <p className="px-1 opacity-70">Расклады не отозвались. Попробуй позже.</p>
        ) : spreadsQuery.data && spreadsQuery.data.length > 0 ? (
          <div className="flex flex-col gap-3">
            {spreadsQuery.data.map((s) => (
              // HOME-06: wire SpreadCard.onSelect -> setSpread. The chosen spread gets an
              // accent ring on its wrapper (the selected affordance) without mislabeling the
              // card's «рекомендуем» badge, which stays bound to the topic recommendation.
              <div
                key={s.slug}
                className="rounded-xl"
                style={
                  spreadSlug === s.slug
                    ? { boxShadow: "0 0 0 2px var(--deck-accent)" }
                    : undefined
                }
              >
                <SpreadCard
                  spread={s}
                  recommended={
                    recommendation.data?.recommended_spread.slug === s.slug
                  }
                  onSelect={setSpread}
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="px-1 opacity-60">Здесь пока пусто.</p>
        )}
      </section>

      {/*
        Sticky «Начать расклад» CTA (HOME-07 / UI-01 / UI-04). Pinned to the bottom, accent-
        filled (Color reserved-for #1), full-width minus md gutters. Bottom padding comes from
        the Telegram SDK safe-area insets (getSafeAreaInsets / getContentSafeAreaInsets) — NOT
        env()/100vh — so it clears the home indicator (Pitfall 3 / T-3-06). The pinned band
        is sized against the Telegram-provided viewportStableHeight var (keyboard-safe: the
        iOS keyboard can't hide the CTA); `top: auto` keeps it bottom-anchored.
      */}
      <div
        className="fixed inset-x-0 bottom-0 px-4 pt-3"
        style={{
          paddingBottom:
            16 +
            Math.max(
              getSafeAreaInsets().bottom,
              getContentSafeAreaInsets().bottom,
            ),
          background:
            "linear-gradient(to top, var(--deck-bg) 60%, transparent)",
          // Keyboard-safe anchor: stay within the stable viewport height the keyboard leaves
          // (Telegram-provided var; falls back to the visual viewport). Never 100vh/env().
          maxHeight: "var(--tg-viewport-stable-height, 100dvh)",
        }}
      >
        {!ready && !startError && (
          <p className="px-1 pb-2 text-center text-sm opacity-70">
            {START_GATE_HINT}
          </p>
        )}
        {startError ? (
          // D-08 failure UX: the soft §9.8 line + Повторить (re-run same, free) + Сменить
          // колоду (back to deck selection, question preserved). No spinner — the ritual,
          // not this screen, covers the real latency (D-07).
          <div className="flex flex-col gap-3">
            <p
              className="px-1 text-center text-sm"
              style={{ color: "var(--deck-soft)" }}
            >
              {READING_ERROR}
            </p>
            <div className="flex gap-3">
              <m.button
                type="button"
                whileTap={{ scale: 0.97 }}
                disabled={isStarting}
                onClick={handleStart}
                aria-disabled={isStarting}
                className="flex-1 rounded-2xl px-4 py-4 text-base font-semibold outline-none transition-opacity focus-visible:ring-2 disabled:opacity-50"
                style={{
                  background: "var(--deck-accent)",
                  color: "var(--deck-bg)",
                  boxShadow: "0 14px 44px -18px var(--deck-accent)",
                }}
              >
                {READING_RETRY}
              </m.button>
              <m.button
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={handleChangeDeck}
                className="flex-1 rounded-2xl border px-4 py-4 text-base font-semibold outline-none focus-visible:ring-2"
                style={{
                  color: "var(--deck-soft)",
                  borderColor:
                    "color-mix(in srgb, var(--deck-soft) 36%, transparent)",
                  background: "transparent",
                }}
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
            className="w-full rounded-2xl px-4 py-4 text-base font-semibold outline-none transition-opacity focus-visible:ring-2 disabled:opacity-50"
            style={{
              background: "var(--deck-accent)",
              color: "var(--deck-bg)",
              boxShadow: ready
                ? "0 14px 44px -18px var(--deck-accent)"
                : "none",
            }}
          >
            {START_CTA}
          </m.button>
        )}
      </div>
    </main>
  );
}

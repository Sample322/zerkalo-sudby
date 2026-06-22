import { useState } from "react";
import { AnimatePresence } from "motion/react";
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
} from "../reading/copy";
import { questionValidity, useSelection, type AnswerStyle } from "../stores/selection";
import { useDeckTheme } from "../theme/useDeckTheme";
import { DeckCard } from "./DeckCard";
import { PaywallSheet } from "./PaywallSheet";
import { SpreadCard } from "./SpreadCard";
import { ThrottleToast } from "./ThrottleToast";
import { TopicChip } from "./TopicChip";
import type { Deck } from "../api/decks";
import type { Recommendation, Spread } from "../api/spreads";

/** 7 days in milliseconds — the pre-emptive paywall reset moment is `week_start + 7d` (06-02). */
const WEEK_MS = 7 * 86_400_000;

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

// The selection wizard sub-steps, in order. One focus per page (Вопрос → Тема → Колода →
// Расклад), each its own screen with back/change — far calmer than the old single dense screen,
// and it adapts cleanly from a 360px phone to a wide desktop window.
type WizardStep = "question" | "topic" | "deck" | "spread" | "style";
const WIZARD_ORDER: readonly WizardStep[] = ["question", "topic", "deck", "spread", "style"];
const STEP_TITLE: Record<WizardStep, string> = {
  question: "Твой вопрос",
  topic: "Выбери тему",
  deck: "Выбери колоду",
  spread: "Выбери расклад",
  style: "Стиль ответа",
};

/** The 3 answer-style options shown on the final wizard step (label + a one-line hint). */
const ANSWER_STYLE_OPTIONS: { key: AnswerStyle; label: string; hint: string }[] = [
  { key: "yasny", label: "Ясный", hint: "По существу и конкретно, с практичным выводом." },
  { key: "berezhny", label: "Бережный", hint: "Тепло и понятно — и смысл, и атмосфера." },
  { key: "tainstvenny", label: "Таинственный", hint: "Образно, голосом оракула, с метафорами." },
];

const PAGE_TRANSITION = { duration: 0.32, ease: [0.16, 1, 0.3, 1] as const };

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
  const answerStyle = useSelection((s) => s.answerStyle);
  const setAnswerStyle = useSelection((s) => s.setAnswerStyle);
  const setQuestion = useSelection((s) => s.setQuestion);
  const setReading = useSelection((s) => s.setReading);
  const goTo = useSelection((s) => s.goTo);

  const decksQuery = useDecks();
  const spreadsQuery = useSpreads(topic, deckSlug);
  const recommendation = useRecommendation(topic, deckSlug);

  const meQuery = useMe();
  const reversalsEnabled = meQuery.data?.settings.reversals_enabled ?? localReversals;

  const limits = meQuery.data?.limits;
  const unlimited = limits?.unlimited ?? false;
  const freeLeft = limits
    ? Math.max(0, limits.free_weekly_limit - limits.free_used_this_week)
    : undefined;

  // Open on the furthest already-chosen step so returning to selection (or a deep-linked store)
  // resumes where the user left off instead of forcing the whole wizard again.
  const [wizardStep, setWizardStep] = useState<WizardStep>(() =>
    spreadSlug ? "style" : deckSlug ? "spread" : topic ? "deck" : "question",
  );
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState(false);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paywallResetAt, setPaywallResetAt] = useState<string | null>(null);
  const [throttleOpen, setThrottleOpen] = useState(false);

  const selectedSpread = spreadsQuery.data?.find((s) => s.slug === spreadSlug);
  const stepIndex = WIZARD_ORDER.indexOf(wizardStep);

  function goToStep(step: WizardStep): void {
    setStartError(false);
    setWizardStep(step);
  }

  function back(): void {
    if (stepIndex > 0) goToStep(WIZARD_ORDER[stepIndex - 1]);
  }

  // Auto-advance on a discrete choice (D: «каждый выбор = переход на след. страницу»); the
  // selection is preserved in the store, so going back shows it highlighted and re-picking
  // re-advances.
  function pickTopic(slug: string): void {
    setTopic(slug);
    goToStep("deck");
  }
  function pickDeck(slug: string): void {
    setDeck(slug);
    goToStep("spread");
  }
  function pickSpread(slug: string): void {
    setSpread(slug);
    goToStep("style");
  }

  async function handleStart() {
    if (isStarting || !selectedSpread || !topic || !deckSlug || !spreadSlug) return;
    // Pre-emptive paywall — skipped for the unlimited allowlist (admin + testers never pre-block).
    if (!unlimited && freeLeft === 0) {
      setPaywallResetAt(computeResetAt(limits?.week_start));
      setPaywallOpen(true);
      return;
    }
    setIsStarting(true);
    setStartError(false);
    try {
      const reading = await createReading({
        question: question.trim().length === 0 ? null : question, // D-13: empty => general
        topic,
        deckSlug,
        spreadSlug,
        reversalsEnabled,
        positions: selectedSpread.positions,
        // RU labels for the result meta (the slugs go to the backend; these go on screen).
        deckTitle: decksQuery.data?.find((d) => d.slug === deckSlug)?.title,
        spreadTitle: selectedSpread.title,
        topicLabel: TOPICS.find((t) => t.slug === topic)?.label,
        answerStyle,
      });
      setReading(reading);
      goTo("ritual");
    } catch (err) {
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

  const isEmptyQuestion = question.trim().length === 0;
  const questionHint = isEmptyQuestion
    ? QUESTION_EMPTY_HELPER
    : questionValidity(question).status === "tooShort"
      ? QUESTION_TOO_SHORT_HINT
      : null;

  const insetBottom =
    16 + Math.max(getSafeAreaInsets().bottom, getContentSafeAreaInsets().bottom);

  return (
    <main className="mx-auto flex min-h-full w-full max-w-xl flex-1 flex-col px-5 pb-32 pt-6">
      {/* Wizard header — back (or brand) + step progress + the home nav on the first page. */}
      <header className="flex items-center justify-between gap-3">
        {stepIndex > 0 ? (
          <m.button
            type="button"
            whileTap={{ scale: 0.92 }}
            onClick={back}
            aria-label="Назад"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-[18px] outline-none focus-visible:ring-2"
            style={{
              background: "color-mix(in srgb, var(--deck-deep) 50%, transparent)",
              border: "1px solid color-mix(in srgb, var(--deck-accent) 26%, transparent)",
              color: "var(--deck-accent)",
              cursor: "pointer",
            }}
          >
            <span aria-hidden="true">←</span>
          </m.button>
        ) : (
          <span className="eyebrow">Зеркало Судьбы</span>
        )}

        <Progress index={stepIndex} total={WIZARD_ORDER.length} />

        {stepIndex === 0 ? (
          <nav aria-label="Навигация" className="flex items-center gap-2">
            <NavButton label={HISTORY_HEADER} glyph="⟲" onClick={() => goTo("history")} />
            <NavButton label={PROFILE_HEADER} glyph="☾" onClick={() => goTo("profile")} />
          </nav>
        ) : (
          <span className="h-11 w-11 shrink-0" aria-hidden="true" />
        )}
      </header>

      <div className="mt-7 flex flex-col items-center gap-1 text-center">
        <span className="eyebrow">{`Шаг ${stepIndex + 1} из ${WIZARD_ORDER.length}`}</span>
        <h1 className="font-display metal-text text-[30px] leading-tight">{STEP_TITLE[wizardStep]}</h1>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <m.section
          key={wizardStep}
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -18 }}
          transition={PAGE_TRANSITION}
          className="mt-8 flex flex-1 flex-col"
        >
          {wizardStep === "question" && (
            <div className="flex flex-col gap-3">
              {/* HOME-01/02/D-13 — the single untrusted input (T-3-01). Controlled; text is only a
                  React text node. The store clamps to QUESTION_MAX. Question is optional. */}
              <textarea
                id="reading-question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={QUESTION_PLACEHOLDER}
                rows={4}
                className="panel w-full resize-none p-5 text-[19px] italic leading-relaxed outline-none placeholder:not-italic focus-visible:ring-2"
                style={{ color: "var(--deck-soft)" }}
              />
              <p className="px-1 text-center text-[15px]" style={{ color: "var(--color-mist-dim)" }}>
                {questionHint ?? "Можно начать и без вопроса — расклад будет общим."}
              </p>
            </div>
          )}

          {wizardStep === "topic" && (
            <div className="flex flex-wrap justify-center gap-3">
              {TOPICS.map((t) => (
                <TopicChip key={t.slug} topic={t.slug} label={t.label} active={topic === t.slug} onSelect={pickTopic} />
              ))}
            </div>
          )}

          {wizardStep === "deck" && (
            <DeckStep
              isPending={decksQuery.isPending}
              isError={decksQuery.isError}
              decks={decksQuery.data}
              selected={deckSlug}
              onPick={pickDeck}
            />
          )}

          {wizardStep === "spread" && (
            <SpreadStep
              isPending={spreadsQuery.isPending}
              isError={spreadsQuery.isError}
              spreads={spreadsQuery.data}
              selected={spreadSlug}
              recommendedSlug={recommendation.data?.recommended_spread.slug}
              recommendation={recommendation.data}
              onSelect={pickSpread}
            />
          )}

          {wizardStep === "style" && (
            <StyleStep selected={answerStyle} onSelect={setAnswerStyle} />
          )}
        </m.section>
      </AnimatePresence>

      {/* Footer CTA — «Далее» on the question step; «Начать расклад» (+ limits) on the final style
          step. Topic/deck/spread steps auto-advance on a choice, so they have no footer button. */}
      <div
        className="fixed inset-x-0 bottom-0 z-20 mx-auto w-full max-w-xl px-5 pt-3"
        style={{
          paddingBottom: insetBottom,
          background: "linear-gradient(to top, var(--deck-bg) 70%, transparent)",
          maxHeight: "var(--tg-viewport-stable-height, 100dvh)",
        }}
      >
        {wizardStep === "question" && (
          <m.button
            type="button"
            whileTap={{ scale: 0.97 }}
            onClick={() => goToStep("topic")}
            className="pill-primary w-full py-4 text-[18px] outline-none focus-visible:ring-2"
          >
            Далее
          </m.button>
        )}

        {wizardStep === "style" && (
          <SpreadFooter
            ready={Boolean(spreadSlug)}
            isStarting={isStarting}
            startError={startError}
            limits={limits}
            freeLeft={freeLeft}
            unlimited={unlimited}
            onStart={handleStart}
            onRetry={handleStart}
            onChangeDeck={() => {
              setStartError(false);
              goToStep("deck");
            }}
          />
        )}
      </div>

      <PaywallSheet open={paywallOpen} resetAt={paywallResetAt} onDismiss={() => setPaywallOpen(false)} />
      <ThrottleToast open={throttleOpen} onDismiss={() => setThrottleOpen(false)} />
    </main>
  );
}

/** Step-progress dots. */
function Progress({ index, total }: { index: number; total: number }) {
  return (
    <div className="flex items-center gap-2" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className="h-1.5 rounded-full transition-all duration-300"
          style={{
            width: i === index ? 20 : 6,
            background: "var(--deck-accent)",
            opacity: i === index ? 1 : i < index ? 0.6 : 0.28,
          }}
        />
      ))}
    </div>
  );
}

/** Loading/empty helper line (shared by the deck + spread steps). */
function Muted({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-1 text-center text-[16px] italic" style={{ color: "var(--color-mist-dim)" }}>
      {children}
    </p>
  );
}

function DeckStep({
  isPending,
  isError,
  decks,
  selected,
  onPick,
}: {
  isPending: boolean;
  isError: boolean;
  decks: Deck[] | undefined;
  selected: string | null;
  onPick: (slug: string) => void;
}) {
  if (isPending) return <Muted>Колода раскладывается…</Muted>;
  if (isError) return <Muted>Колода сейчас молчит. Загляни чуть позже.</Muted>;
  if (!decks || decks.length === 0) return <Muted>Колоды ещё в тишине.</Muted>;
  return (
    <div className="flex flex-wrap justify-center gap-4">
      {decks.map((deck) => (
        <DeckCard key={deck.slug} deck={deck} active={deck.slug === selected} onSelect={onPick} />
      ))}
    </div>
  );
}

function SpreadStep({
  isPending,
  isError,
  spreads,
  selected,
  recommendedSlug,
  recommendation,
  onSelect,
}: {
  isPending: boolean;
  isError: boolean;
  spreads: Spread[] | undefined;
  selected: string | null;
  recommendedSlug: string | undefined;
  recommendation: Recommendation | undefined;
  onSelect: (slug: string) => void;
}) {
  if (isPending) return <Muted>Расклады собираются…</Muted>;
  if (isError) return <Muted>Расклады не отозвались. Попробуй позже.</Muted>;
  if (!spreads || spreads.length === 0) return <Muted>Здесь пока пусто.</Muted>;
  return (
    <div className="flex flex-col gap-4">
      {recommendation && (
        <div
          className="panel-altar relative overflow-hidden p-4 text-center"
        >
          <p className="eyebrow">Колода советует</p>
          <p className="font-display mt-1 text-[19px]" style={{ color: "var(--deck-soft)" }}>
            {recommendation.recommended_spread.title}
          </p>
          <p className="mt-1.5 text-[15px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
            {recommendation.reason}
          </p>
        </div>
      )}
      {spreads.map((s) => (
        <div
          key={s.slug}
          className="rounded-[18px]"
          style={
            selected === s.slug
              ? {
                  boxShadow:
                    "0 0 0 1.5px var(--deck-accent), 0 0 26px -8px color-mix(in srgb, var(--deck-glow) 75%, transparent)",
                }
              : undefined
          }
        >
          <SpreadCard spread={s} recommended={recommendedSlug === s.slug} onSelect={onSelect} />
        </div>
      ))}
    </div>
  );
}

/** The final wizard step — pick how the reading should sound (Ясный/Бережный/Таинственный). */
function StyleStep({
  selected,
  onSelect,
}: {
  selected: AnswerStyle;
  onSelect: (style: AnswerStyle) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      {ANSWER_STYLE_OPTIONS.map((opt) => {
        const active = selected === opt.key;
        return (
          <m.button
            key={opt.key}
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelect(opt.key)}
            aria-pressed={active}
            className="panel flex flex-col gap-1 p-5 text-left"
            style={
              active
                ? {
                    borderColor: "color-mix(in srgb, var(--deck-accent) 55%, transparent)",
                    boxShadow:
                      "0 0 0 1.5px var(--deck-accent), 0 0 26px -8px color-mix(in srgb, var(--deck-glow) 75%, transparent)",
                  }
                : undefined
            }
          >
            <span className="font-display metal-text text-[22px] leading-tight">{opt.label}</span>
            <span className="text-[15px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
              {opt.hint}
            </span>
          </m.button>
        );
      })}
    </div>
  );
}

/** The final-step footer: remaining-count + «Начать расклад», or the soft failure band. */
function SpreadFooter({
  ready,
  isStarting,
  startError,
  limits,
  freeLeft,
  unlimited,
  onStart,
  onRetry,
  onChangeDeck,
}: {
  ready: boolean;
  isStarting: boolean;
  startError: boolean;
  limits: { free_weekly_limit: number } | undefined;
  freeLeft: number | undefined;
  unlimited: boolean;
  onStart: () => void;
  onRetry: () => void;
  onChangeDeck: () => void;
}) {
  if (startError) {
    return (
      <div className="flex flex-col gap-3">
        <p className="px-1 text-center text-[16px] italic" style={{ color: "var(--deck-soft)" }}>
          {READING_ERROR}
        </p>
        <div className="flex gap-3">
          <m.button
            type="button"
            whileTap={{ scale: 0.97 }}
            disabled={isStarting}
            onClick={onRetry}
            className="pill-primary flex-1 px-4 py-4 text-[17px] outline-none transition-opacity focus-visible:ring-2 disabled:opacity-50"
          >
            {READING_RETRY}
          </m.button>
          <m.button
            type="button"
            whileTap={{ scale: 0.97 }}
            onClick={onChangeDeck}
            className="pill-ghost flex-1 px-4 py-4 text-[17px] outline-none focus-visible:ring-2"
          >
            {READING_CHANGE_DECK}
          </m.button>
        </div>
      </div>
    );
  }

  return (
    <>
      {unlimited ? (
        <p className="px-1 pb-2 text-center text-[15px]" style={{ color: "var(--deck-accent)" }}>
          ✦&nbsp;Безлимит
        </p>
      ) : (
        limits &&
        freeLeft !== undefined &&
        freeLeft > 0 && (
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
        )
      )}
      <m.button
        type="button"
        whileTap={{ scale: 0.97 }}
        disabled={!ready || isStarting}
        onClick={onStart}
        aria-disabled={!ready || isStarting}
        className="pill-primary w-full px-4 py-4 text-[18px] outline-none transition-all focus-visible:ring-2 disabled:opacity-40"
        style={ready ? undefined : { boxShadow: "none", filter: "saturate(0.6)" }}
      >
        {START_CTA}
      </m.button>
    </>
  );
}

/** A refined glass circle for the History / Profile entry points (first wizard page). */
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

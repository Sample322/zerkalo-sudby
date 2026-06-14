import type { CSSProperties } from "react";
import { useState } from "react";
import * as m from "motion/react-m";
import type { PanInfo } from "motion/react";

import {
  useDeleteReading,
  useReadingsList,
  useRestoreReading,
} from "../../hooks/useReadings";
import { useSelection } from "../../stores/selection";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import { CardArt } from "../CardArtFallback";
import {
  HISTORY_EMPTY,
  HISTORY_ERROR,
  HISTORY_GENERAL,
  HISTORY_HEADER,
  HISTORY_LAST_TEN_NOTE,
  HISTORY_LOADING,
  NAV_BACK,
} from "../../reading/copy";
import type { ReadingListItem } from "../../api/readings";
import { UndoSnackbar } from "./UndoSnackbar";

// HistoryScreen — the History list (HIST-01/02/06). Reverse-chronological list backed by
// useReadingsList against GET /api/readings (server state — Query, never Zustand). Each item
// shows date / question (or «Общий расклад») / deck / spread / card thumbnails / short summary
// (TZ §9.6). Empty → the §9.6 copy. Back affordance → back() returns Home (D-11). Tapping a
// card sets detailReadingId + goTo("readingDetail") — 05-06 wires the immutable detail render.
// All copy comes from copy.ts (SAFE-06). The question/summary are TEXT nodes (T-05-XSS — no
// dangerouslySetInnerHTML). Registered in FlowRoot under the `history` step.
//
// Swipe-to-delete (HIST-04 / D-03): swiping a card left past the threshold optimistically
// removes it (useDeleteReading on the ["readings","list"] key) and raises an UndoSnackbar (~5s,
// motion only). «Отменить» restores it (useRestoreReading re-inserts the cached item); after
// the window lapses the removal stands (the server already soft-deleted). An equivalent
// accessible delete button backs the swipe so the affordance is keyboard-reachable.

/** Leftward drag distance (px) past which a swipe commits the delete. */
const SWIPE_DELETE_THRESHOLD = 96;

// Accessible name for the swipe-delete control (the swipe is the visual affordance; this is its
// keyboard-reachable twin). Kept local + non-visible — copy.ts is locked this plan (the user-
// facing snackbar strings already live there); brand-safe, contains no banned token (SAFE-06).
const DELETE_READING_LABEL = "Убрать расклад из истории";

// Deterministic DD.MM.YYYY from the ISO date part (mirrors ResultScreen.formatDate — no
// timezone drift, no locale dependency).
function formatDate(iso: string): string {
  const [y, mo, d] = iso.slice(0, 10).split("-");
  return d && mo && y ? `${d}.${mo}.${y}` : iso;
}

const GLASS: CSSProperties = {
  background: "color-mix(in srgb, var(--deck-deep) 70%, transparent)",
  border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
  borderRadius: 16,
};

/** The reading currently inside the undo window (one at a time), with its original index. */
interface PendingDelete {
  item: ReadingListItem;
  index: number;
}

export function HistoryScreen() {
  const back = useSelection((s) => s.back);
  const setDetailReadingId = useSelection((s) => s.setDetailReadingId);
  const goTo = useSelection((s) => s.goTo);
  const insets = getContentSafeAreaInsets();

  const { data, isPending, isError } = useReadingsList();
  const deleteReadingMutation = useDeleteReading();
  const restoreReadingMutation = useRestoreReading();

  // The reading awaiting undo (drives the snackbar). null → no snackbar shown.
  const [pending, setPending] = useState<PendingDelete | null>(null);

  function openReading(item: ReadingListItem): void {
    setDetailReadingId(item.reading_id);
    goTo("readingDetail");
  }

  // Swipe/keyboard delete: optimistically remove + offer undo. The DELETE runs in the
  // background (optimistic mutation); the snapshot/rollback lives in useDeleteReading.
  function handleDelete(item: ReadingListItem, index: number): void {
    setPending({ item, index });
    deleteReadingMutation.mutate(item.reading_id);
  }

  // «Отменить» — restore the cached item at its original slot, then dismiss the snackbar.
  function handleUndo(): void {
    if (!pending) return;
    restoreReadingMutation.mutate({
      id: pending.item.reading_id,
      item: pending.item,
      index: pending.index,
    });
    setPending(null);
  }

  // Window lapsed (or dismissed): the optimistic removal stands (server already soft-deleted).
  function handleDismiss(): void {
    setPending(null);
  }

  const items = data ?? [];

  return (
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-12"
      style={{ paddingTop: 16 + insets.top, color: "var(--deck-soft)" }}
    >
      <header className="flex items-center gap-3">
        <m.button
          type="button"
          whileTap={{ scale: 0.94 }}
          onClick={back}
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
          {HISTORY_HEADER}
        </h1>
      </header>

      {isPending ? (
        <p className="px-1 opacity-70">{HISTORY_LOADING}</p>
      ) : isError ? (
        <p className="px-1 opacity-70">{HISTORY_ERROR}</p>
      ) : items.length === 0 ? (
        // §9.6 empty state — soft, inviting (no fatalism, no brand tokens).
        <p className="px-1 text-base leading-relaxed opacity-80">{HISTORY_EMPTY}</p>
      ) : (
        <>
          <section className="flex flex-col gap-4">
            {items.map((item, index) => (
              <HistoryCard
                key={item.reading_id}
                item={item}
                onOpen={() => openReading(item)}
                onDelete={() => handleDelete(item, index)}
              />
            ))}
          </section>

          {/* Quiet «последние 10» note (D-04); the subscription upsell is Phase 6/7. */}
          <p className="px-1 text-center text-xs opacity-50">{HISTORY_LAST_TEN_NOTE}</p>
        </>
      )}

      {/* HIST-04 undo affordance — one snackbar at a time, motion only (no toast lib). */}
      <UndoSnackbar open={pending !== null} onUndo={handleUndo} onDismiss={handleDismiss} />
    </main>
  );
}

interface HistoryCardProps {
  item: ReadingListItem;
  /** Tap (or Enter on the card body) → reopen the immutable reading. */
  onOpen: () => void;
  /** Swipe-left past the threshold, or the explicit delete button → soft-delete + undo. */
  onDelete: () => void;
}

// One history list card. The whole card is a horizontal drag surface (motion `drag="x"`); a
// leftward swipe past the threshold commits the delete and the card snaps back (the optimistic
// cache removal then unmounts it). Tap-to-open is preserved on the inner body button. A small
// explicit delete button is the keyboard-reachable twin of the swipe (and the test's trigger).
function HistoryCard({ item, onOpen, onDelete }: HistoryCardProps) {
  function handleDragEnd(_event: unknown, info: PanInfo): void {
    if (info.offset.x <= -SWIPE_DELETE_THRESHOLD) onDelete();
  }

  return (
    <m.div
      className="relative"
      drag="x"
      dragSnapToOrigin
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.4}
      onDragEnd={handleDragEnd}
      style={{ ...GLASS, touchAction: "pan-y" }}
    >
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full flex-col gap-3 p-4 pr-12 text-left outline-none focus-visible:ring-2"
        style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
      >
        {/* Date eyebrow + question (or general label — text nodes, T-05-XSS). */}
        <div className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide opacity-50">
            {formatDate(item.created_at)}
          </span>
          <span className="text-lg font-semibold" style={{ color: "var(--deck-accent)" }}>
            {item.question && item.question.trim().length > 0 ? item.question : HISTORY_GENERAL}
          </span>
        </div>

        {/* Deck · spread meta row. */}
        <div className="flex flex-wrap gap-x-2 text-sm opacity-70">
          <span>{item.deck_name}</span>
          <span aria-hidden="true">·</span>
          <span>{item.spread_name}</span>
        </div>

        {/* Card thumbnails — CardArt covers missing art with the CSS/SVG fallback (A2).
            CardArt is a fixed 120×192; we down-scale it into a 44×70 box (overflow
            hidden + transform-origin top-left so the scaled art fills the slot). */}
        {item.card_thumbnails.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {item.card_thumbnails.map((src, i) => (
              <div
                key={`${item.reading_id}-thumb-${i}`}
                className="shrink-0 overflow-hidden"
                style={{ width: 44, height: 70, borderRadius: 6 }}
              >
                <div style={{ transform: "scale(0.3667)", transformOrigin: "top left" }}>
                  <CardArt src={src || null} alt={`${item.deck_name} — карта ${i + 1}`} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Short summary (§9.6 короткий итог — never the full interpretation). */}
        {item.summary_short && (
          <p className="text-sm leading-relaxed opacity-80">{item.summary_short}</p>
        )}
      </button>

      {/* Keyboard-reachable delete (the swipe's accessible twin). Stops propagation so it never
          opens the reading. Non-visible label kept local — copy.ts is locked this plan. */}
      <m.button
        type="button"
        whileTap={{ scale: 0.9 }}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        aria-label={DELETE_READING_LABEL}
        className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full outline-none focus-visible:ring-2"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 60%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
          color: "var(--deck-accent)",
          cursor: "pointer",
        }}
      >
        <span aria-hidden="true">✕</span>
      </m.button>
    </m.div>
  );
}

export default HistoryScreen;

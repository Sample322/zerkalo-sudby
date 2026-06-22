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
// useReadingsList (server state — Query). Each item shows date / question / deck / spread / card
// thumbnails / short summary. Tapping opens the immutable detail; swipe-left (or the ✕ twin)
// optimistically soft-deletes with an UndoSnackbar. All copy from copy.ts (SAFE-06); values are
// TEXT nodes (T-05-XSS).

/** Leftward drag distance (px) past which a swipe commits the delete. */
const SWIPE_DELETE_THRESHOLD = 96;

const DELETE_READING_LABEL = "Убрать расклад из истории";

// Deterministic DD.MM.YYYY from the ISO date part.
function formatDate(iso: string): string {
  const [y, mo, d] = iso.slice(0, 10).split("-");
  return d && mo && y ? `${d}.${mo}.${y}` : iso;
}

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

  const [pending, setPending] = useState<PendingDelete | null>(null);

  function openReading(item: ReadingListItem): void {
    setDetailReadingId(item.reading_id);
    goTo("readingDetail");
  }

  function handleDelete(item: ReadingListItem, index: number): void {
    setPending({ item, index });
    deleteReadingMutation.mutate(item.reading_id);
  }

  function handleUndo(): void {
    if (!pending) return;
    restoreReadingMutation.mutate({ id: pending.item.reading_id, item: pending.item, index: pending.index });
    setPending(null);
  }

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
        <div className="flex flex-col">
          <span className="eyebrow">Зеркало помнит</span>
          <h1 className="font-display metal-text text-[28px] leading-tight">{HISTORY_HEADER}</h1>
        </div>
      </header>

      {isPending ? (
        <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_LOADING}</p>
      ) : isError ? (
        <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_ERROR}</p>
      ) : items.length === 0 ? (
        <p className="px-1 text-[17px] italic leading-relaxed" style={{ color: "var(--color-mist)" }}>
          {HISTORY_EMPTY}
        </p>
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

          <p className="px-1 text-center text-[13px]" style={{ color: "var(--color-mist-dim)" }}>
            {HISTORY_LAST_TEN_NOTE}
          </p>
        </>
      )}

      <UndoSnackbar open={pending !== null} onUndo={handleUndo} onDismiss={handleDismiss} />
    </main>
  );
}

interface HistoryCardProps {
  item: ReadingListItem;
  onOpen: () => void;
  onDelete: () => void;
}

function HistoryCard({ item, onOpen, onDelete }: HistoryCardProps) {
  function handleDragEnd(_event: unknown, info: PanInfo): void {
    if (info.offset.x <= -SWIPE_DELETE_THRESHOLD) onDelete();
  }

  return (
    <m.div
      className="panel relative"
      drag="x"
      dragSnapToOrigin
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.4}
      onDragEnd={handleDragEnd}
      style={{ touchAction: "pan-y" }}
    >
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full flex-col gap-3 p-4 pr-12 text-left outline-none focus-visible:ring-2"
        style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
      >
        <div className="flex flex-col gap-1">
          <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
            {formatDate(item.created_at)}
          </span>
          <span className="font-display metal-text text-[19px] leading-tight">
            {item.question && item.question.trim().length > 0 ? item.question : HISTORY_GENERAL}
          </span>
        </div>

        <div className="flex flex-wrap gap-x-2 text-[14px]" style={{ color: "var(--color-mist-dim)" }}>
          <span>{item.deck_name}</span>
          <span aria-hidden="true">·</span>
          <span>{item.spread_name}</span>
        </div>

        {/* Card thumbnails — CardArt (120×192) down-scaled into a 44×70 slot. */}
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

        {item.summary_short && (
          <p className="text-[15px] leading-relaxed" style={{ color: "color-mix(in srgb, var(--color-mist) 84%, transparent)" }}>
            {item.summary_short}
          </p>
        )}
      </button>

      <m.button
        type="button"
        whileTap={{ scale: 0.9 }}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        aria-label={DELETE_READING_LABEL}
        className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full text-[13px] outline-none focus-visible:ring-2"
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

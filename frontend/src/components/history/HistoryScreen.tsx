// HistoryScreen — the History list (HIST-01/02/06). This plan (05-05) ships the real body
// (Task 2): a load-more list backed by useReadingsList against GET /api/readings, the §9.6
// empty state, and an in-app back → Home (D-11). Registered in FlowRoot under the `history`
// step. The screen registry is `() => Element`, so this always returns an element.
//
// NOTE (Task 1 nav-spine commit): this is the placeholder shell; Task 2 fills the list body.

import { useSelection } from "../../stores/selection";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import { HISTORY_HEADER, NAV_BACK } from "../../reading/copy";

export function HistoryScreen() {
  const back = useSelection((s) => s.back);
  const insets = getContentSafeAreaInsets();

  return (
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-12"
      style={{ paddingTop: 16 + insets.top, color: "var(--deck-soft)" }}
    >
      <header className="flex items-center gap-3">
        <button
          type="button"
          onClick={back}
          aria-label={NAV_BACK}
          className="grid h-10 w-10 place-items-center rounded-full outline-none focus-visible:ring-2"
          style={{
            background: "color-mix(in srgb, var(--deck-deep) 60%, transparent)",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
            color: "var(--deck-accent)",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true">←</span>
        </button>
        <h1 className="text-3xl font-semibold" style={{ color: "var(--deck-accent)" }}>
          {HISTORY_HEADER}
        </h1>
      </header>
    </main>
  );
}

export default HistoryScreen;

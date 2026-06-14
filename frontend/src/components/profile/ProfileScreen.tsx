// ProfileScreen — Phase-5 navigation STUB (D-07). This plan (05-05) owns ALL shared FE seams
// so 05-07 (the real profile/settings body — Telegram identity + the reversals /
// history-personalization toggles via GET /api/me + PATCH /api/me/settings) replaces ONLY
// this file, mirroring the Phase-3 FlowRoot-stub pattern (no multi-writer conflict).
//
// It renders a brand-safe placeholder with an in-app back affordance → Home (D-11). The
// FlowRoot screen registry is `() => Element`, so this must always return an element.

import * as m from "motion/react-m";

import { useSelection } from "../../stores/selection";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import { NAV_BACK, PROFILE_HEADER } from "../../reading/copy";

export function ProfileScreen() {
  const back = useSelection((s) => s.back);
  const insets = getContentSafeAreaInsets();

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
          className="grid h-10 w-10 place-items-center rounded-full outline-none focus-visible:ring-2"
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
          {PROFILE_HEADER}
        </h1>
      </header>
    </main>
  );
}

export default ProfileScreen;

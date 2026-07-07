// ProfileScreen — the Profile/Settings surface (PROF-01 / PROF-02 / D-07). Shows the Telegram
// identity (name + photo from `GET /api/me`) and the two user-facing toggles — reversals and
// history-personalization — each persisted via `PATCH /api/me/settings` with an OPTIMISTIC cache
// update. The personalization toggle defaults OFF and carries a plain-language privacy explainer
// (SAFE-06 — all strings from copy.ts, never the mechanism).
//
// FREE-COUNT BLOCK (D-09, Phase 6): a small glass block between identity and settings shows the
// FREE count ONLY (formatRemaining) — subscription/paid surface stays out until Phase 7.
//
// Renders inside FlowRoot's <LazyMotion features={domAnimation}> (m.* only). Identity values are
// React text nodes (T-05-XSS).

import * as m from "motion/react-m";

import { track } from "../../api/events";
import { useMe, usePatchSettings } from "../../hooks/useMe";
import { useCancelSubscription } from "../../hooks/usePayments";
import { useSelection } from "../../stores/selection";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import type { SessionSettings, SessionUser } from "../../api/auth";
import {
  HISTORY_ERROR,
  HISTORY_LOADING,
  NAV_BACK,
  PROFILE_HEADER,
  PROFILE_LIMIT_LABEL,
  SETTINGS_PERSONALIZATION_EXPLAINER,
  SETTINGS_PERSONALIZATION_LABEL,
  SETTINGS_REVERSALS_LABEL,
  SHOP_BALANCE_LABEL,
  SHOP_CANCEL_SUB,
  SHOP_SUB_ACTIVE_PREFIX,
  SHOP_SUBSCRIPTION_LABEL,
} from "../../reading/copy";
import { formatRemaining } from "../../reading/limitCopy";
import { ShopTariffs } from "../shop/ShopTariffs";

/** Format an ISO subscription end as «DD.MM» for the «активна до …» badge (UTC, locale-free). */
function formatPeriodEnd(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${dd}.${mm}`;
}

/** Compose the display name from the Telegram profile, falling back gracefully when absent. */
function displayName(user: SessionUser): string {
  const parts = [user.first_name, user.last_name].filter(
    (p): p is string => Boolean(p && p.trim().length > 0),
  );
  if (parts.length > 0) return parts.join(" ");
  if (user.username) return `@${user.username}`;
  return "Странник"; // brand-safe neutral fallback (SAFE-06).
}

/** Initial for the avatar fallback when no photo_url is present. */
function avatarInitial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "·";
}

interface SettingRowProps {
  label: string;
  description?: string;
  checked: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}

/** One settings toggle row — a label (+ optional explainer) and an accessible switch button. */
function SettingRow({ label, description, checked, disabled, onChange }: SettingRowProps) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-4">
        <span className="text-[17px]" style={{ color: "var(--deck-soft)" }}>
          {label}
        </span>
        <m.button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-label={label}
          disabled={disabled}
          whileTap={disabled ? undefined : { scale: 0.94 }}
          onClick={() => onChange(!checked)}
          className="relative h-7 w-12 shrink-0 rounded-full outline-none transition-colors focus-visible:ring-2 disabled:opacity-50"
          style={{
            background: checked
              ? "linear-gradient(180deg, var(--deck-soft), var(--deck-accent))"
              : "color-mix(in srgb, var(--deck-soft) 24%, transparent)",
            boxShadow: checked ? "0 4px 14px color-mix(in srgb, var(--deck-accent) 36%, transparent)" : undefined,
            cursor: disabled ? "default" : "pointer",
          }}
        >
          <span
            aria-hidden="true"
            className="absolute top-0.5 h-6 w-6 rounded-full transition-[left]"
            style={{ left: checked ? 22 : 2, background: "var(--deck-bg)" }}
          />
        </m.button>
      </div>
      {description && (
        <p className="text-[15px] leading-relaxed" style={{ color: "var(--color-mist-dim)" }}>
          {description}
        </p>
      )}
    </div>
  );
}

/** Shared back-header — eyebrow + title + a single in-app back affordance → Home (D-11). */
function ProfileHeader({ onBack, topInset }: { onBack: () => void; topInset: number }) {
  return (
    <header className="flex items-center gap-3" style={{ paddingTop: 16 + topInset }}>
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
      <div className="flex flex-col">
        <span className="eyebrow">Твой путь</span>
        <h1 className="font-display metal-text text-[28px] leading-tight">{PROFILE_HEADER}</h1>
      </div>
    </header>
  );
}

export function ProfileScreen() {
  const back = useSelection((s) => s.back);
  const goTo = useSelection((s) => s.goTo);
  const insets = getContentSafeAreaInsets();

  const { data, isPending, isError } = useMe();
  const patchSettings = usePatchSettings();
  const cancelSub = useCancelSubscription();

  function toggle(flag: keyof SessionSettings, next: boolean): void {
    patchSettings.mutate({ [flag]: next });
    track("settings_changed", { setting: flag, value: next }); // ANALYTICS-01 (best-effort)
  }

  const body = (() => {
    if (isPending) {
      return <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_LOADING}</p>;
    }
    if (isError || !data) {
      return <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_ERROR}</p>;
    }

    const name = displayName(data.user);
    const settings = data.settings;
    const limits = data.limits;
    // A const local so the guard narrows it to `string` inside the cancel button's onClick closure.
    const subId = limits?.subscription_id ?? null;

    return (
      <>
        {/* Telegram identity — photo (or an initial fallback) + name. */}
        <section className="panel flex items-center gap-4 p-5">
          {data.user.photo_url ? (
            <img
              src={data.user.photo_url}
              alt=""
              width={60}
              height={60}
              referrerPolicy="no-referrer"
              className="h-[60px] w-[60px] shrink-0 rounded-full object-cover"
              style={{ border: "1px solid color-mix(in srgb, var(--deck-accent) 40%, transparent)", boxShadow: "0 0 18px -4px color-mix(in srgb, var(--deck-glow) 60%, transparent)" }}
            />
          ) : (
            <span
              aria-hidden="true"
              className="font-display grid h-[60px] w-[60px] shrink-0 place-items-center rounded-full text-2xl"
              style={{
                background: "color-mix(in srgb, var(--deck-accent) 16%, transparent)",
                border: "1px solid color-mix(in srgb, var(--deck-accent) 36%, transparent)",
                color: "var(--deck-accent)",
              }}
            >
              {avatarInitial(name)}
            </span>
          )}
          <span className="font-display metal-text text-[24px] leading-tight">{name}</span>
        </section>

        {/* Free-readings count (D-09) — free count ONLY (no subscription/paid/buy — Phase 7). */}
        {data.limits && (
          <section className="panel flex flex-col gap-1 p-5">
            <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
              {PROFILE_LIMIT_LABEL}
            </span>
            <span
              className="font-display text-[20px]"
              style={{ color: data.limits.unlimited ? "var(--deck-accent)" : "var(--deck-soft)" }}
            >
              {data.limits.unlimited
                ? "✦ Безлимит"
                : formatRemaining(
                    Math.max(0, data.limits.free_weekly_limit - data.limits.free_used_this_week),
                    data.limits.free_weekly_limit,
                  )}
            </span>
          </section>
        )}

        {/* Баланс / Магазин (D-12) — paid balance, the active-sub badge + cancel, and the tariffs. */}
        <section aria-label={SHOP_BALANCE_LABEL} className="flex flex-col gap-3">
          {limits && (
            <div className="panel flex flex-col gap-1 p-5">
              <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
                {SHOP_BALANCE_LABEL}
              </span>
              <span className="font-display text-[20px]" style={{ color: "var(--deck-soft)" }}>
                {limits.paid_spreads_balance}
              </span>
              {limits.subscription_active && limits.subscription_period_end && (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-[15px]" style={{ color: "var(--deck-accent)" }}>
                    {SHOP_SUBSCRIPTION_LABEL} — {SHOP_SUB_ACTIVE_PREFIX}
                    {formatPeriodEnd(limits.subscription_period_end)}
                  </span>
                  {subId && (
                    <m.button
                      type="button"
                      whileTap={cancelSub.isPending ? undefined : { scale: 0.96 }}
                      disabled={cancelSub.isPending}
                      onClick={() => cancelSub.mutate(subId)}
                      className="pill-ghost px-4 py-2 text-[14px] outline-none focus-visible:ring-2 disabled:opacity-50"
                    >
                      {SHOP_CANCEL_SUB}
                    </m.button>
                  )}
                </div>
              )}
            </div>
          )}
          <ShopTariffs variant="profile" />
        </section>

        {/* The two user-facing toggles (D-07). */}
        <section aria-label="Настройки" className="flex flex-col gap-3">
          <SettingRow
            label={SETTINGS_REVERSALS_LABEL}
            checked={settings.reversals_enabled}
            disabled={false}
            onChange={(next) => toggle("reversals_enabled", next)}
          />
          <SettingRow
            label={SETTINGS_PERSONALIZATION_LABEL}
            description={SETTINGS_PERSONALIZATION_EXPLAINER}
            checked={settings.allow_history_personalization}
            disabled={false}
            onChange={(next) => toggle("allow_history_personalization", next)}
          />
        </section>

        {/* Admin dashboard entry — shown only when the server reports this user is an admin. */}
        {data.is_admin && (
          <m.button
            type="button"
            whileTap={{ scale: 0.97 }}
            onClick={() => goTo("admin")}
            className="pill-ghost w-full py-3.5 text-[16px] outline-none focus-visible:ring-2"
          >
            ✦&nbsp;Админ-панель
          </m.button>
        )}
      </>
    );
  })();

  return (
    <main className="flex min-h-full flex-col gap-6 px-6 pb-12" style={{ color: "var(--deck-soft)" }}>
      <ProfileHeader onBack={back} topInset={insets.top} />
      {body}
    </main>
  );
}

export default ProfileScreen;

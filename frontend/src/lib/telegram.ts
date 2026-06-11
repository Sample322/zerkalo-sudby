// Telegram WebApp bridge. The Mini App runs inside Telegram's WebView, which injects
// `window.Telegram.WebApp`. The only trustworthy identity material is `initData` — a
// signed query string the backend re-validates (two-stage HMAC). The frontend NEVER
// parses identity from it; it forwards the raw string verbatim (threat T-05-01).

/** Inset rectangle (px) reported by Telegram for notches / system chrome (Bot API 8.0). */
export interface TgInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/** Telegram's HapticFeedback surface (a subset — the methods this app uses). */
interface TelegramHapticFeedback {
  impactOccurred?: (
    style: "light" | "medium" | "heavy" | "rigid" | "soft",
  ) => void;
  notificationOccurred?: (type: "error" | "success" | "warning") => void;
  selectionChanged?: () => void;
}

/** Minimal shape of the Telegram WebApp object we rely on. */
interface TelegramWebApp {
  /** Signed init payload — empty string outside a real Telegram WebView. */
  initData?: string;
  /** Signals to Telegram the Mini App is ready to be shown. */
  ready?: () => void;
  /** Expands the WebView to full height. */
  expand?: () => void;
  /** Active color scheme; default to "dark" (premium baseline) when absent. */
  colorScheme?: "light" | "dark";
  /** Theme palette (bg_color, text_color, …) — empty outside Telegram. */
  themeParams?: Record<string, string>;
  /** Safe-area insets for notches / system bars (Bot API 8.0). */
  safeAreaInset?: TgInsets;
  /** Content safe-area insets (inside the Telegram chrome). */
  contentSafeAreaInset?: TgInsets;
  /** Haptic feedback engine — absent outside a real device. */
  HapticFeedback?: TelegramHapticFeedback;
}

interface TelegramNamespace {
  WebApp?: TelegramWebApp;
}

declare global {
  interface Window {
    Telegram?: TelegramNamespace;
  }
}

/**
 * Read the raw `initData` string Telegram injects into the WebView.
 *
 * In a real Telegram client this is a signed query string. Outside Telegram
 * (a plain browser) it is absent, so we fall back to a dev-only mock from
 * `VITE_DEV_INIT_DATA` — gated on `import.meta.env.DEV` so the mock can NEVER
 * ship in a production build. Returns `""` (never throws) when nothing is present.
 */
export function getInitData(): string {
  const fromTelegram = window.Telegram?.WebApp?.initData;
  if (fromTelegram) {
    return fromTelegram;
  }

  // Dev fallback only: lets us exercise the FE -> BE -> JWT flow in a local browser
  // without a real Telegram WebView. Never reachable in a production bundle.
  if (import.meta.env.DEV) {
    return import.meta.env.VITE_DEV_INIT_DATA ?? "";
  }

  return "";
}

/**
 * Tell Telegram the Mini App is ready and expand the viewport.
 * No-op outside a Telegram WebView (the methods simply aren't present).
 */
export function telegramReady(): void {
  const webApp = window.Telegram?.WebApp;
  webApp?.ready?.();
  webApp?.expand?.();
}

const ZERO_INSETS: TgInsets = { top: 0, bottom: 0, left: 0, right: 0 };

/**
 * The active color scheme. Defaults to "dark" — the premium-dark deck canvas stays
 * dominant even when Telegram is in light mode (UI-04 / TZ §21.1).
 */
export function getColorScheme(): "light" | "dark" {
  return window.Telegram?.WebApp?.colorScheme ?? "dark";
}

/** Telegram's theme palette (bg_color, text_color, …). Empty object outside Telegram. */
export function getThemeParams(): Record<string, string> {
  return window.Telegram?.WebApp?.themeParams ?? {};
}

/**
 * Safe-area insets via the Telegram SDK (UI-04 mandates SDK insets, NOT CSS `env()`).
 * All-zeros outside a real WebView so layout never collapses.
 */
export function getSafeAreaInsets(): TgInsets {
  return window.Telegram?.WebApp?.safeAreaInset ?? ZERO_INSETS;
}

/** Content safe-area insets (inside the Telegram chrome). All-zeros when absent. */
export function getContentSafeAreaInsets(): TgInsets {
  return window.Telegram?.WebApp?.contentSafeAreaInset ?? ZERO_INSETS;
}

/**
 * Haptic feedback (UI-03 / READ-07/08). Every method is optional-chained exactly like
 * `telegramReady` so a call is a silent no-op outside Telegram (plain browser / tests).
 *   - impact("light")     — per card flip (READ-08)
 *   - notify("success")   — ritual completion (READ-07)
 *   - selection()         — optional chip/deck tap feedback
 */
export const haptic = {
  impact: (
    style: "light" | "medium" | "heavy" | "rigid" | "soft" = "light",
  ): void => window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(style),
  notify: (type: "error" | "success" | "warning"): void =>
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.(type),
  selection: (): void =>
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged?.(),
};

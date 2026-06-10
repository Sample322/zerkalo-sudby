// Telegram WebApp bridge. The Mini App runs inside Telegram's WebView, which injects
// `window.Telegram.WebApp`. The only trustworthy identity material is `initData` — a
// signed query string the backend re-validates (two-stage HMAC). The frontend NEVER
// parses identity from it; it forwards the raw string verbatim (threat T-05-01).

/** Minimal shape of the Telegram WebApp object we rely on. */
interface TelegramWebApp {
  /** Signed init payload — empty string outside a real Telegram WebView. */
  initData?: string;
  /** Signals to Telegram the Mini App is ready to be shown. */
  ready?: () => void;
  /** Expands the WebView to full height. */
  expand?: () => void;
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

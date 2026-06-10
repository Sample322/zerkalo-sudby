/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL, e.g. http://localhost:8000 (see .env.example). */
  readonly VITE_API_BASE: string;
  /**
   * DEV-ONLY mock Telegram initData string, used to exercise the auth flow in a
   * plain browser when no Telegram WebView is present. Read only under
   * import.meta.env.DEV — never shipped to production. See .env.example.
   */
  readonly VITE_DEV_INIT_DATA?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite 7 (NOT 8 — Rolldown default is deferred to post-MVP).
// The backend base URL is read from VITE_API_BASE at build/serve time
// (see frontend/.env.example); it is never hardcoded in source.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
  // Vitest runs unit tests (e.g. the initData reader) in a jsdom DOM so `window`
  // exists; test files live next to source as *.test.ts and are excluded from the
  // production tsc build (see tsconfig.app.json).
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});

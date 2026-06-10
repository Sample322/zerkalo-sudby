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
});

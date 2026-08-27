import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

/** Proxy API calls to the local FastAPI backend (`uvicorn backend.app:app`). */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:7870",
        changeOrigin: true,
        // Large PDF detect can take several minutes; default proxy idle
        // timeouts would otherwise abort with an empty body.
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
    },
  },
});

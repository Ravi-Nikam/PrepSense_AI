import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the Django backend, so the browser talks to the
// same origin and we don't need CORS configured on the backend. In Docker the
// target is the `web` service; locally it defaults to localhost:8000.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true },
    },
  },
});

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_PROXY_TARGET ?? "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Same-origin /api in dev mirrors the nginx proxy in Docker, so the client never
      // needs to know the backend host and CORS only matters for split deployments.
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true, ws: true },
        "/uploads": { target: apiTarget, changeOrigin: true },
      },
    },
  };
});

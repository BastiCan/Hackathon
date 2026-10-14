import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El frontend consume la API en localhost:8000. Usamos un proxy en /api
// para evitar problemas de CORS en desarrollo.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

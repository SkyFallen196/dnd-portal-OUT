import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Настройки Vite. Фронтенд поднимается на порту 5173.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});

import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// El build va directo a ../static para que Flask lo sirva sin Node instalado.
export default defineConfig({
  base: "/static/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:5055" },
  },
});

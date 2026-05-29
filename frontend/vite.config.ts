/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  plugins: [react(), tailwindcss()],
  base: "/static/react-dist/",
  build: {
    outDir: "../app/static/react-dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    manifest: "manifest.json",
    rollupOptions: {
      input: [
        path.resolve(__dirname, "src/pages/index/index.html"),
        path.resolve(__dirname, "src/pages/control-novedades/index.html"),
        path.resolve(__dirname, "src/pages/urgencias/index.html"),
        path.resolve(__dirname, "src/pages/odontologia/index.html"),
        path.resolve(__dirname, "src/pages/odontologia-equipos-basicos/index.html"),
        path.resolve(__dirname, "src/pages/derechos/index.html"),
        path.resolve(__dirname, "src/pages/ordenado-facturado/index.html"),
        path.resolve(__dirname, "src/pages/usuarios/index.html"),
        path.resolve(__dirname, "src/pages/genderize/index.html"),
        path.resolve(__dirname, "src/pages/login/index.html"),
        path.resolve(__dirname, "src/pages/unauthorized/index.html"),
        path.resolve(__dirname, "src/pages/abiertas-urgencias/index.html"),
        path.resolve(__dirname, "src/pages/catalogo/index.html"),
      ],
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});

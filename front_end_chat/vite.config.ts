import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    assetsDir: "assets",
    rollupOptions: {
      output: {
        entryFileNames: `assets/index-fixed.js`,
        chunkFileNames: `assets/[name]-fixed.js`,
        assetFileNames: `assets/[name]-fixed[extname]`,
      },
    },
  },
});
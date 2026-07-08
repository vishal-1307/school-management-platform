import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import vercel from "@astrojs/vercel";

// https://astro.build/config
export default defineConfig({
  site: "https://knowledgeacademy.edu.in",
  // Static by default: all public pages stay prerendered/CDN-cached.
  // Portal pages opt into on-demand rendering with `export const prerender = false`.
  output: "static",
  adapter: vercel(),
  integrations: [react()],
  vite: {
    plugins: [tailwindcss()],
  },
});

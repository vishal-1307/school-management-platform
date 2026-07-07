import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import vercel from "@astrojs/vercel";
import clerk from "@clerk/astro";

// Clerk is only wired in when a publishable key exists; without it the
// portals run in DEV_AUTH mode (role picker on /sign-in, demo only).
const hasClerk = Boolean(process.env.PUBLIC_CLERK_PUBLISHABLE_KEY);

// https://astro.build/config
export default defineConfig({
  site: "https://knowledgeacademy.edu.in",
  // Static by default: all public pages stay prerendered/CDN-cached.
  // Portal pages opt into on-demand rendering with `export const prerender = false`.
  output: "static",
  adapter: vercel(),
  integrations: [react(), ...(hasClerk ? [clerk()] : [])],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: hasClerk
        ? {}
        : {
            // Without the Clerk integration its virtual modules don't exist,
            // so point component/server imports at local stubs. Pages branch
            // on the same env flag before using them.
            "@clerk/astro/components": fileURLToPath(
              new URL("./src/lib/clerk-stub.ts", import.meta.url),
            ),
            "@clerk/astro/server": fileURLToPath(
              new URL("./src/lib/clerk-stub.ts", import.meta.url),
            ),
          },
    },
    build: {
      rollupOptions: {
        // @clerk/astro/server has a conditional Cloudflare-runtime import;
        // it never executes on Vercel but Rollup must not try to bundle it.
        external: ["cloudflare:workers"],
      },
    },
  },
});

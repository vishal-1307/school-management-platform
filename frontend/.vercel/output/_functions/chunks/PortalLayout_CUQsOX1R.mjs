import { e as createAstro, f as createComponent, h as addAttribute, n as renderHead, o as renderSlot, r as renderTemplate } from './astro/server_Y12UPm38.mjs';
import 'piccolore';
import 'clsx';
/* empty css                         */

const $$Astro = createAstro("https://knowledgeacademy.edu.in");
const $$PortalLayout = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$Astro, $$props, $$slots);
  Astro2.self = $$PortalLayout;
  const { title } = Astro2.props;
  return renderTemplate`<html lang="en"> <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="generator"${addAttribute(Astro2.generator, "content")}><meta name="robots" content="noindex"><title>${title}</title><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"><meta name="theme-color" content="#4F46E5">${renderHead()}</head> <body class="min-h-screen bg-slate-50 text-slate-900 font-body antialiased"> ${renderSlot($$result, $$slots["default"])} </body></html>`;
}, "C:/HDDD/Projects/Knowledge/frontend/src/layouts/PortalLayout.astro", void 0);

export { $$PortalLayout as $ };

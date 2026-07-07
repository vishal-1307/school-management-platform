import { f as createComponent, k as renderComponent, r as renderTemplate } from '../chunks/astro/server_Y12UPm38.mjs';
import 'piccolore';
import { $ as $$PortalLayout } from '../chunks/PortalLayout_CUQsOX1R.mjs';
export { renderers } from '../renderers.mjs';

const prerender = false;
const $$Portal = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "PortalLayout", $$PortalLayout, { "title": "Opening your portal\u2026" }, { "default": ($$result2) => renderTemplate` ${renderComponent($$result2, "PortalDispatcher", null, { "client:only": "react", "client:component-hydration": "only", "client:component-path": "C:/HDDD/Projects/Knowledge/frontend/src/components/portal/PortalDispatcher.tsx", "client:component-export": "default" })} ` })}`;
}, "C:/HDDD/Projects/Knowledge/frontend/src/pages/portal.astro", void 0);

const $$file = "C:/HDDD/Projects/Knowledge/frontend/src/pages/portal.astro";
const $$url = "/portal";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$Portal,
  file: $$file,
  prerender,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };

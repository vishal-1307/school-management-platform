import { f as createComponent, k as renderComponent, r as renderTemplate } from '../chunks/astro/server_Y12UPm38.mjs';
import 'piccolore';
import { $ as $$PortalLayout } from '../chunks/PortalLayout_CUQsOX1R.mjs';
export { renderers } from '../renderers.mjs';

const prerender = false;
const $$Index = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "PortalLayout", $$PortalLayout, { "title": "Teacher Dashboard \u2014 Knowledge Academy" }, { "default": ($$result2) => renderTemplate` ${renderComponent($$result2, "TeacherDashboard", null, { "client:only": "react", "client:component-hydration": "only", "client:component-path": "C:/HDDD/Projects/Knowledge/frontend/src/components/teacher/TeacherDashboard.tsx", "client:component-export": "default" })} ` })}`;
}, "C:/HDDD/Projects/Knowledge/frontend/src/pages/teacher/index.astro", void 0);

const $$file = "C:/HDDD/Projects/Knowledge/frontend/src/pages/teacher/index.astro";
const $$url = "/teacher";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$Index,
  file: $$file,
  prerender,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };

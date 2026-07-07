import { f as createComponent, k as renderComponent, r as renderTemplate, m as maybeRenderHead } from '../chunks/astro/server_Y12UPm38.mjs';
import 'piccolore';
import { $ as $$PortalLayout } from '../chunks/PortalLayout_CUQsOX1R.mjs';
import { jsxs, jsx } from 'react/jsx-runtime';
import { useState } from 'react';
import { p as publicGet } from '../chunks/api_C97hcNo1.mjs';
export { renderers } from '../renderers.mjs';

const ROLES = [
  { role: "super_admin", portal: "/admin", label: "Admin", desc: "Full control — students, fees, exams, website" },
  { role: "teacher", portal: "/teacher", label: "Teacher", desc: "Attendance, homework, marks for assigned classes" },
  { role: "student", portal: "/student", label: "Student", desc: "Timetable, homework, results, fee status" }
];
function DevRolePicker() {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const enter = async (role, portal) => {
    setBusy(role);
    setError("");
    const health = await publicGet("/health", 6e4);
    if (!health) {
      setError("Backend is unreachable. If it was recently deployed it may be waking up — try again in a minute.");
      setBusy(null);
      return;
    }
    localStorage.setItem("auth_token", `dev:${role}`);
    document.cookie = `dev_role=${role}; path=/; max-age=86400; samesite=lax`;
    window.location.href = portal;
  };
  return /* @__PURE__ */ jsxs("div", { className: "max-w-md w-full mx-auto space-y-4", children: [
    /* @__PURE__ */ jsx("div", { className: "p-4 bg-amber-50 border border-amber-200 rounded-2xl text-amber-800 text-xs font-bold", children: "DEMO MODE — Clerk sign-in is not configured yet, so you can enter any portal directly. Real logins with passwords take over automatically once Clerk keys are added." }),
    ROLES.map(({ role, portal, label, desc }) => /* @__PURE__ */ jsxs(
      "button",
      {
        type: "button",
        disabled: busy !== null,
        onClick: () => enter(role, portal),
        className: "w-full bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition text-left disabled:opacity-60",
        children: [
          /* @__PURE__ */ jsx("p", { className: "font-extrabold text-slate-900", children: busy === role ? "Entering…" : `${label} Portal` }),
          /* @__PURE__ */ jsx("p", { className: "text-xs text-slate-500 font-semibold mt-1", children: desc })
        ]
      },
      role
    )),
    error && /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3", children: error })
  ] });
}

const prerender = false;
const $$SignIn = createComponent(async ($$result, $$props, $$slots) => {
  const hasClerk = Boolean(undefined                                            );
  let SignIn = null;
  if (hasClerk) {
    ({ SignIn } = await import('../chunks/clerk-stub_CZdzXkn0.mjs'));
  }
  return renderTemplate`${renderComponent($$result, "PortalLayout", $$PortalLayout, { "title": "Sign In — Knowledge Development Kindergarten Academy" }, { "default": async ($$result2) => renderTemplate` ${maybeRenderHead()}<section class="min-h-screen flex flex-col items-center justify-center px-4 py-16 space-y-8"> <a href="/" class="text-center space-y-1"> <p class="font-heading font-extrabold text-2xl text-slate-900">Knowledge Academy</p> <p class="text-sm font-bold text-indigo-600">Portal Sign In</p> </a> ${hasClerk ? renderTemplate`${renderComponent($$result2, "SignIn", SignIn, { "forceRedirectUrl": "/portal" })}` : renderTemplate`${renderComponent($$result2, "DevRolePicker", DevRolePicker, { "client:load": true, "client:component-hydration": "load", "client:component-path": "C:/HDDD/Projects/Knowledge/frontend/src/components/DevRolePicker.tsx", "client:component-export": "default" })}`} <a href="/" class="text-xs font-bold text-slate-400 hover:text-slate-600">← Back to website</a> </section> ` })}`;
}, "C:/HDDD/Projects/Knowledge/frontend/src/pages/sign-in.astro", void 0);
const $$file = "C:/HDDD/Projects/Knowledge/frontend/src/pages/sign-in.astro";
const $$url = "/sign-in";

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  default: $$SignIn,
  file: $$file,
  prerender,
  url: $$url
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };

import { renderers } from './renderers.mjs';
import { c as createExports, s as serverEntrypointModule } from './chunks/_@astrojs-ssr-adapter_Cc7-rnLJ.mjs';
import { manifest } from './manifest_Dyk51FJp.mjs';

const serverIslandMap = new Map();;

const _page0 = () => import('./pages/_image.astro.mjs');
const _page1 = () => import('./pages/about.astro.mjs');
const _page2 = () => import('./pages/academics.astro.mjs');
const _page3 = () => import('./pages/achievements.astro.mjs');
const _page4 = () => import('./pages/admin.astro.mjs');
const _page5 = () => import('./pages/admissions.astro.mjs');
const _page6 = () => import('./pages/contact.astro.mjs');
const _page7 = () => import('./pages/disclosure.astro.mjs');
const _page8 = () => import('./pages/facilities.astro.mjs');
const _page9 = () => import('./pages/faculty.astro.mjs');
const _page10 = () => import('./pages/gallery.astro.mjs');
const _page11 = () => import('./pages/login.astro.mjs');
const _page12 = () => import('./pages/notices.astro.mjs');
const _page13 = () => import('./pages/portal.astro.mjs');
const _page14 = () => import('./pages/sign-in.astro.mjs');
const _page15 = () => import('./pages/student.astro.mjs');
const _page16 = () => import('./pages/teacher.astro.mjs');
const _page17 = () => import('./pages/index.astro.mjs');
const pageMap = new Map([
    ["node_modules/astro/dist/assets/endpoint/generic.js", _page0],
    ["src/pages/about.astro", _page1],
    ["src/pages/academics.astro", _page2],
    ["src/pages/achievements.astro", _page3],
    ["src/pages/admin/index.astro", _page4],
    ["src/pages/admissions.astro", _page5],
    ["src/pages/contact.astro", _page6],
    ["src/pages/disclosure.astro", _page7],
    ["src/pages/facilities.astro", _page8],
    ["src/pages/faculty.astro", _page9],
    ["src/pages/gallery.astro", _page10],
    ["src/pages/login.astro", _page11],
    ["src/pages/notices.astro", _page12],
    ["src/pages/portal.astro", _page13],
    ["src/pages/sign-in.astro", _page14],
    ["src/pages/student/index.astro", _page15],
    ["src/pages/teacher/index.astro", _page16],
    ["src/pages/index.astro", _page17]
]);

const _manifest = Object.assign(manifest, {
    pageMap,
    serverIslandMap,
    renderers,
    actions: () => import('./noop-entrypoint.mjs'),
    middleware: () => import('./_astro-internal_middleware.mjs')
});
const _args = {
    "middlewareSecret": "8dbc637f-2de6-4656-88d9-9113f115e499",
    "skewProtection": false
};
const _exports = createExports(_manifest, _args);
const __astrojsSsrVirtualEntry = _exports.default;
const _start = 'start';
if (Object.prototype.hasOwnProperty.call(serverEntrypointModule, _start)) ;

export { __astrojsSsrVirtualEntry as default, pageMap };

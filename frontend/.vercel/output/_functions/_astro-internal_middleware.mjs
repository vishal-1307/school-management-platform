import { e as defineMiddleware, s as sequence } from './chunks/render-context_CNYC0sHN.mjs';
import 'es-module-lexer';
import './chunks/astro-designed-error-pages_Bvs8v-fw.mjs';
import 'piccolore';
import './chunks/astro/server_Y12UPm38.mjs';
import 'clsx';

const hasClerk = Boolean(undefined                                            );
const PROTECTED = [
  { prefix: "/admin", roles: ["super_admin", "office_admin"] },
  { prefix: "/teacher", roles: ["teacher"] },
  { prefix: "/student", roles: ["student", "parent"] }
];
function requiredRoles(pathname) {
  for (const rule of PROTECTED) {
    if (pathname === rule.prefix || pathname.startsWith(rule.prefix + "/")) {
      return rule.roles;
    }
  }
  return null;
}
let clerkOnRequest = null;
if (hasClerk) {
  const { clerkMiddleware } = await import('./chunks/clerk-stub_CZdzXkn0.mjs');
  clerkOnRequest = clerkMiddleware((auth, context) => {
    const roles = requiredRoles(new URL(context.request.url).pathname);
    if (!roles) return;
    const { userId, sessionClaims } = auth();
    if (!userId) {
      return context.redirect("/sign-in");
    }
    const metadata = sessionClaims?.metadata ?? sessionClaims?.publicMetadata;
    const role = metadata?.role;
    if (role && !roles.includes(role)) {
      return context.redirect("/portal");
    }
  });
}
const devOnRequest = defineMiddleware((context, next) => {
  const roles = requiredRoles(new URL(context.request.url).pathname);
  if (!roles) return next();
  const role = context.cookies.get("dev_role")?.value;
  if (!role) return context.redirect("/sign-in");
  if (!roles.includes(role)) return context.redirect("/portal");
  return next();
});
const onRequest$1 = hasClerk ? clerkOnRequest : devOnRequest;

const onRequest = sequence(
	
	onRequest$1
	
);

export { onRequest };

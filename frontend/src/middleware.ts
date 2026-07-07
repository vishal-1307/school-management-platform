/**
 * Role-gates the portal routes (/admin, /teacher, /student).
 *
 * Clerk mode (PUBLIC_CLERK_PUBLISHABLE_KEY set): requires a signed-in Clerk
 * session; coarse role check uses the session claim `metadata.role` (see
 * docs/SETUP_CLERK.md for the session-token customization). The backend
 * remains the authority — every API call re-checks the role server-side.
 *
 * Dev mode (no Clerk key + PUBLIC_DEV_AUTH=true): gates on the `dev_role`
 * cookie set by the role picker. Demo only.
 *
 * Only runs for non-prerendered pages, which is exactly the portal set.
 */

import { defineMiddleware } from "astro:middleware";

const hasClerk = Boolean(import.meta.env.PUBLIC_CLERK_PUBLISHABLE_KEY);
const devAuth = import.meta.env.PUBLIC_DEV_AUTH === "true";

const PROTECTED: { prefix: string; roles: string[] }[] = [
  { prefix: "/admin", roles: ["super_admin", "office_admin"] },
  { prefix: "/teacher", roles: ["teacher"] },
  { prefix: "/student", roles: ["student", "parent"] },
];

function requiredRoles(pathname: string): string[] | null {
  for (const rule of PROTECTED) {
    if (pathname === rule.prefix || pathname.startsWith(rule.prefix + "/")) {
      return rule.roles;
    }
  }
  return null;
}

let clerkOnRequest: ReturnType<typeof defineMiddleware> | null = null;
if (hasClerk) {
  const { clerkMiddleware } = await import("@clerk/astro/server");
  clerkOnRequest = clerkMiddleware((auth, context) => {
    const roles = requiredRoles(new URL(context.request.url).pathname);
    if (!roles) return;

    const { userId, sessionClaims } = auth();
    if (!userId) {
      return context.redirect("/sign-in");
    }
    // Coarse gate only; undefined role claim falls through to the portal
    // dispatcher + backend /api/auth/me for the authoritative check.
    const metadata = (sessionClaims?.metadata ?? sessionClaims?.publicMetadata) as
      | { role?: string }
      | undefined;
    const role = metadata?.role;
    if (role && !roles.includes(role)) {
      return context.redirect("/portal");
    }
  });
}

const devOnRequest = defineMiddleware((context, next) => {
  const roles = requiredRoles(new URL(context.request.url).pathname);
  if (!roles) return next();

  if (!devAuth) {
    // No auth system configured at all — keep portals closed.
    return context.redirect("/login");
  }
  const role = context.cookies.get("dev_role")?.value;
  if (!role) return context.redirect("/sign-in");
  if (!roles.includes(role)) return context.redirect("/portal");
  return next();
});

export const onRequest = hasClerk ? clerkOnRequest! : devOnRequest;

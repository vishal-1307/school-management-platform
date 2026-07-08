/**
 * Role-gates the portal routes (/admin, /teacher, /student).
 *
 * Reads the "session_token" cookie set at login (see authStore.ts) and
 * verifies it locally with the same HS256 SECRET_KEY the backend uses
 * (set as a Vercel env var — copy the exact value from Render). This is a
 * coarse, fast gate only: the backend independently re-verifies the token
 * and re-checks the role on every API call, so a missing/misconfigured
 * SECRET_KEY here can only make navigation less convenient, never grant
 * access the API wouldn't also grant.
 *
 * Only runs for non-prerendered pages, which is exactly the portal set.
 */

import { defineMiddleware } from "astro:middleware";
import { jwtVerify } from "jose";

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

const secret = import.meta.env.SECRET_KEY
  ? new TextEncoder().encode(import.meta.env.SECRET_KEY)
  : null;

/** Decode the role claim from the session cookie, verifying the signature when possible. */
async function roleFromToken(token: string): Promise<string | null> {
  if (secret) {
    try {
      const { payload } = await jwtVerify(token, secret);
      return (payload.role as string) ?? null;
    } catch {
      return null; // expired/invalid/tampered
    }
  }
  // SECRET_KEY not set on this deployment — fall back to an unverified
  // decode for coarse routing only. The API remains the real gate.
  try {
    const [, payloadB64] = token.split(".");
    const payload = JSON.parse(atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/")));
    return payload.role ?? null;
  } catch {
    return null;
  }
}

export const onRequest = defineMiddleware(async (context, next) => {
  const roles = requiredRoles(new URL(context.request.url).pathname);
  if (!roles) return next();

  const token = context.cookies.get("session_token")?.value;
  if (!token) return context.redirect("/login");

  const role = await roleFromToken(token);
  if (!role) return context.redirect("/login");
  if (!roles.includes(role)) return context.redirect("/portal");

  return next();
});

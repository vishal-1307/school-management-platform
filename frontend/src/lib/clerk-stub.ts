/**
 * Build-time stand-in for "@clerk/astro/components" when Clerk is not
 * configured (no PUBLIC_CLERK_PUBLISHABLE_KEY). The real package needs the
 * Clerk integration's virtual modules, which only exist when the
 * integration is registered in astro.config. Nothing here ever renders —
 * pages branch on the same env flag before using these.
 */

export const SignIn = () => null;
export const SignUp = () => null;
export const UserButton = () => null;

// "@clerk/astro/server" surface
export const clerkMiddleware = () => {
  throw new Error("Clerk is not configured (PUBLIC_CLERK_PUBLISHABLE_KEY is missing)");
};

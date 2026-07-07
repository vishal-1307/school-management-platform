/**
 * Client-side auth state for the portals.
 *
 * The backend /api/auth/me is the authority on role and entity links; this
 * module caches it and wires the api client's token getter to Clerk when
 * present (falling back to the dev token in localStorage otherwise).
 */

import { authFetch, setTokenGetter } from "./api";

export interface Me {
  id: number;
  clerk_id: string;
  email: string | null;
  phone: string | null;
  role: string;
  linked_staff_id: number | null;
  linked_student_id: number | null;
  linked_parent_id: number | null;
  is_active: boolean;
}

declare global {
  interface Window {
    Clerk?: {
      session?: { getToken(): Promise<string | null> } | null;
      signOut?: () => Promise<void>;
    };
  }
}

let wired = false;

/** Point authFetch at Clerk's session token when Clerk is on the page. */
export function wireTokens(): void {
  if (wired) return;
  wired = true;
  setTokenGetter(async () => {
    if (typeof window !== "undefined" && window.Clerk?.session) {
      return window.Clerk.session.getToken();
    }
    return typeof localStorage !== "undefined" ? localStorage.getItem("auth_token") : null;
  });
}

let me: Me | null = null;

export async function getMe(force = false): Promise<Me | null> {
  wireTokens();
  if (me && !force) return me;
  try {
    me = await authFetch<Me>("/api/auth/me");
    return me;
  } catch {
    return null;
  }
}

export function portalHomeFor(role: string): string {
  if (role === "super_admin" || role === "office_admin") return "/admin";
  if (role === "teacher") return "/teacher";
  return "/student";
}

export async function signOut(): Promise<void> {
  me = null;
  if (typeof localStorage !== "undefined") localStorage.removeItem("auth_token");
  if (typeof document !== "undefined") {
    document.cookie = "dev_role=; Max-Age=0; path=/";
  }
  if (typeof window !== "undefined") {
    if (window.Clerk?.signOut) await window.Clerk.signOut();
    window.location.href = "/login";
  }
}

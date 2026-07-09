/**
 * Client-side auth state for the portals.
 *
 * The backend issues a 24h JWT on /api/auth/login. It lives in
 * localStorage ("auth_token") for Authorization headers on API calls, and
 * mirrored in the "session_token" cookie so the server-side middleware can
 * role-gate portal routes. /api/auth/me remains the authority on role and
 * entity links.
 */

import { API_URL, authFetch } from "./api";

export interface Me {
  id: number;
  login_id: string;
  phone: string | null;
  role: string;
  linked_staff_id: number | null;
  linked_student_id: number | null;
  linked_parent_id: number | null;
  is_active: boolean;
  display_name: string;
  class_label: string | null;
}

const TOKEN_KEY = "auth_token";
const COOKIE_NAME = "session_token";
const DAY_SECONDS = 86400;

/** Persist a freshly issued session token (login / password change). */
export function storeSession(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${COOKIE_NAME}=${token}; path=/; max-age=${DAY_SECONDS}; SameSite=Lax${secure}`;
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = `${COOKIE_NAME}=; path=/; Max-Age=0`;
}

let me: Me | null = null;

export async function getMe(force = false): Promise<Me | null> {
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
  try {
    // Best-effort server-side revocation of every session for this account.
    await fetch(`${API_URL}/api/auth/logout`, { method: "POST" });
  } catch {
    /* stateless logout is fine */
  }
  clearSession();
  window.location.href = "/login";
}

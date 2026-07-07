/**
 * Single seam between the frontend and the FastAPI backend.
 *
 * Public helpers never throw for reads: the public website must render its
 * built-in fallback content even when the backend is asleep (Render free
 * tier cold-starts take ~50s) or unreachable.
 */

export const API_URL: string = (
  (import.meta.env.PUBLIC_API_URL as string | undefined) ?? "http://localhost:8000"
).replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 4500;

/** GET a public endpoint. Returns null on any failure (caller keeps fallback). */
export async function publicGet<T>(
  path: string,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T | null> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      signal: AbortSignal.timeout(timeoutMs),
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

/** POST to a public endpoint (forms). Throws with a readable message on failure. */
export async function publicPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

/** Session token supplier — wired to Clerk (or dev auth) by the portal shell. */
export type TokenGetter = () => Promise<string | null> | string | null;

let tokenGetter: TokenGetter = () =>
  typeof localStorage !== "undefined" ? localStorage.getItem("auth_token") : null;

export function setTokenGetter(getter: TokenGetter): void {
  tokenGetter = getter;
}

/** Authenticated request for portal pages. Throws on failure. */
export async function authFetch<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const token = await tokenGetter();
  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* keep default */
    }
    const error = new Error(detail) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Authenticated request returning raw text (certificates, receipts). */
export async function authFetchText(path: string): Promise<string> {
  const token = await tokenGetter();
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.text();
}

/** Open an authenticated HTML document (TC, receipt) in a print-ready tab. */
export async function openHtmlDocument(path: string): Promise<void> {
  const html = await authFetchText(path);
  const win = window.open("", "_blank");
  if (!win) throw new Error("Popup blocked — allow popups for this site");
  win.document.open();
  win.document.write(html);
  win.document.close();
}

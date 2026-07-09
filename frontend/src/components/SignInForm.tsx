/**
 * Single institutional login form (LPU-UMS style): one login ID + password
 * field for every role. The backend's own response decides which portal
 * the user lands in — there's no separate admin/teacher/student page.
 */

import { useEffect, useRef, useState } from "react";
import { API_URL } from "../lib/api";
import { portalHomeFor, storeSession } from "../lib/authStore";

interface LoginResponse {
  token: string;
  user: { role: string };
}

const WAKE_HINT_DELAY_MS = 4000;

export default function SignInForm() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showWakeHint, setShowWakeHint] = useState(false);
  const [error, setError] = useState("");
  const [showForgot, setShowForgot] = useState(false);
  const wakeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (wakeTimer.current) clearTimeout(wakeTimer.current);
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId.trim() || !password) {
      setError("Enter your login ID and password");
      return;
    }
    setBusy(true);
    setError("");
    setShowWakeHint(false);
    // Only show the "waking up" message if the request is still in flight
    // after a few seconds — most logins (warm backend) never see it.
    wakeTimer.current = setTimeout(() => setShowWakeHint(true), WAKE_HINT_DELAY_MS);

    try {
      // One request, one wait — no separate pre-flight health check. Render
      // free tier cold starts take up to ~50s, so the timeout is generous.
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login_id: loginId.trim(), password }),
        signal: AbortSignal.timeout(60000),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(
          response.status === 429
            ? "Too many attempts — please wait 15 minutes and try again."
            : data.detail || "Invalid ID or password",
        );
        return;
      }

      const body = (await response.json()) as LoginResponse;
      storeSession(body.token);
      window.location.href = portalHomeFor(body.user.role);
    } catch {
      setError(
        "Couldn't reach the server. If this is the first sign-in in a while it may be waking up — please try again.",
      );
    } finally {
      if (wakeTimer.current) clearTimeout(wakeTimer.current);
      setShowWakeHint(false);
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="w-full max-w-sm space-y-5 bg-white p-8 rounded-3xl border border-slate-100 shadow-lg shadow-slate-200/50"
    >
      <div className="space-y-1">
        <h1 className="text-xl font-extrabold font-heading text-slate-900">Log in</h1>
        <p className="text-xs font-semibold text-slate-400">Portal Sign In</p>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-600">Login ID</label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 3.5-6 8-6s8 2 8 6" />
            </svg>
          </span>
          <input
            type="text"
            autoComplete="username"
            autoFocus
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            placeholder="e.g. ADM-00001 or EMP-001"
            className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-600">Password</label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="5" y="11" width="14" height="9" rx="2" />
              <path d="M8 11V7a4 4 0 118 0v4" />
            </svg>
          </span>
          <input
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full pl-11 pr-11 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            {showPassword ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 5.1A9.9 9.9 0 0121 12s-1.6 3-4.6 5M6.6 6.6C4.6 8 3 12 3 12s3.5 7 9 7c1.3 0 2.5-.3 3.6-.8" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">
          {error}
        </p>
      )}
      {busy && showWakeHint && (
        <p className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
          Waking up the server — the first sign-in after a quiet period can take up to a minute.
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-bold rounded-xl transition"
      >
        {busy ? "Signing in…" : "Login"}
      </button>

      <div className="text-center">
        <button
          type="button"
          onClick={() => setShowForgot((v) => !v)}
          className="text-xs font-bold text-indigo-600 hover:underline"
        >
          Forgot your password?
        </button>
        {showForgot && (
          <p className="mt-2 text-xs text-slate-500 font-semibold">
            Passwords are issued by the school office. Contact them with your Login ID to get a
            reset.
          </p>
        )}
      </div>

      <p className="text-xs text-slate-400 font-semibold text-center border-t border-slate-100 pt-4">
        Students, parents, teachers, and admin all sign in here with the login ID and password
        issued by the school office.
      </p>
    </form>
  );
}

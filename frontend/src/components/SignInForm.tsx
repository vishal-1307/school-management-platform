/**
 * Single institutional login form (LPU-UMS style): one login ID + password
 * field for every role. The backend's own response decides which portal
 * the user lands in — there's no separate admin/teacher/student page.
 */

import { useState } from "react";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { API_URL, publicGet } from "../lib/api";
import { portalHomeFor, storeSession } from "../lib/authStore";

interface LoginResponse {
  token: string;
  user: { role: string };
}

const FIRST_ATTEMPT_TIMEOUT_MS = 20000;
const WAKE_POLL_INTERVAL_MS = 4000;
const WAKE_POLL_MAX_MS = 120000; // Render cold boot + Neon autosuspend wake can stack up

async function attemptLogin(loginId: string, password: string): Promise<Response> {
  return fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login_id: loginId, password }),
    signal: AbortSignal.timeout(FIRST_ATTEMPT_TIMEOUT_MS),
  });
}

export default function SignInForm() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [showForgot, setShowForgot] = useState(false);

  const finishWithResponse = async (response: Response) => {
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
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = loginId.trim();
    if (!id || !password) {
      setError("Enter your login ID and password");
      return;
    }
    setBusy(true);
    setError("");
    setStatusMessage("");

    try {
      const response = await attemptLogin(id, password);
      await finishWithResponse(response);
      return;
    } catch {
      // Network error or timeout — most likely a cold Render instance (and
      // possibly a suspended Neon compute underneath it). Don't just fail:
      // poll /health until the backend is actually reachable, then retry
      // the login automatically so the user never has to click again.
    }

    setStatusMessage("Waking up the server — this can take up to a couple of minutes on the first sign-in after a quiet period.");
    const deadline = Date.now() + WAKE_POLL_MAX_MS;
    let awake = false;
    while (Date.now() < deadline) {
      const health = await publicGet<{ status: string }>("/health", WAKE_POLL_INTERVAL_MS);
      if (health) {
        awake = true;
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, WAKE_POLL_INTERVAL_MS));
    }

    if (!awake) {
      setStatusMessage("");
      setError("The server is taking longer than usual to wake up. Please try again in a minute.");
      setBusy(false);
      return;
    }

    setStatusMessage("Server is up — signing you in…");
    try {
      const response = await attemptLogin(id, password);
      await finishWithResponse(response);
    } catch {
      setError("Couldn't reach the server. Please try again.");
    } finally {
      setStatusMessage("");
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
            <User className="w-[18px] h-[18px]" />
          </span>
          <input
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoFocus
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            placeholder="e.g. ADM-00001 or EMP-001"
            className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-base sm:text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-600">Password</label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
            <Lock className="w-[18px] h-[18px]" />
          </span>
          <input
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full pl-11 pr-11 py-3 bg-slate-50 border border-slate-200 rounded-xl text-base sm:text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute right-0.5 top-1/2 -translate-y-1/2 p-3 rounded-lg text-slate-400 hover:text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            {showPassword ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">
          {error}
        </p>
      )}
      {busy && statusMessage && (
        <p className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex items-center gap-2">
          <span className="w-3 h-3 border-2 border-amber-300 border-t-amber-700 rounded-full animate-spin flex-shrink-0" />
          {statusMessage}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-bold rounded-xl transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
      >
        {busy ? "Signing in…" : "Login"}
      </button>

      <div className="text-center">
        <button
          type="button"
          onClick={() => setShowForgot((v) => !v)}
          className="text-xs font-bold text-indigo-600 hover:underline p-2 -m-2 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
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

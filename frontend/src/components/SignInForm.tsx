/**
 * Single institutional login form (LPU-UMS style): one login ID + password
 * field for every role. The backend's own response decides which portal
 * the user lands in — there's no separate admin/teacher/student page.
 */

import { useState } from "react";
import { API_URL, publicGet } from "../lib/api";
import { portalHomeFor, storeSession } from "../lib/authStore";

interface LoginResponse {
  token: string;
  user: { role: string };
}

export default function SignInForm() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId.trim() || !password) {
      setError("Enter your login ID and password");
      return;
    }
    setBusy(true);
    setError("");
    try {
      // Wake the backend first — Render free tier cold-starts take ~50s,
      // and a plain login POST would otherwise just look like it hung.
      const health = await publicGet<{ status: string }>("/health", 60000);
      if (!health) {
        setError(
          "Can't reach the server right now. If it was just deployed it may be waking up — try again in a minute.",
        );
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login_id: loginId.trim(), password }),
        signal: AbortSignal.timeout(30000),
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
      setError("Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="w-full max-w-sm space-y-5 bg-white p-8 rounded-3xl border border-slate-100 shadow-sm">
      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-600">Login ID</label>
        <input
          type="text"
          autoComplete="username"
          autoFocus
          value={loginId}
          onChange={(e) => setLoginId(e.target.value)}
          placeholder="e.g. ADM-00001 or EMP-001"
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-600">Password</label>
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition"
        />
      </div>

      {error && (
        <p className="text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-bold rounded-xl transition"
      >
        {busy ? "Signing in…" : "Sign In"}
      </button>

      <p className="text-xs text-slate-400 font-semibold text-center">
        Students, parents, teachers, and admin all sign in here with the login ID and password
        issued by the school office.
      </p>
    </form>
  );
}

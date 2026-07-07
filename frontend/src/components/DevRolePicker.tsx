/**
 * Demo-only sign-in used while Clerk is not configured (PUBLIC_DEV_AUTH).
 * Picks a role, stores the dev bearer token + cookie, and enters the portal.
 */

import { useState } from "react";
import { publicGet } from "../lib/api";

const ROLES = [
  { role: "super_admin", portal: "/admin", label: "Admin", desc: "Full control — students, fees, exams, website" },
  { role: "teacher", portal: "/teacher", label: "Teacher", desc: "Attendance, homework, marks for assigned classes" },
  { role: "student", portal: "/student", label: "Student", desc: "Timetable, homework, results, fee status" },
];

export default function DevRolePicker() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const enter = async (role: string, portal: string) => {
    setBusy(role);
    setError("");
    // Wake the backend first (Render free tier may be cold-starting).
    const health = await publicGet<{ status: string }>("/health", 60000);
    if (!health) {
      setError("Backend is unreachable. If it was recently deployed it may be waking up — try again in a minute.");
      setBusy(null);
      return;
    }
    localStorage.setItem("auth_token", `dev:${role}`);
    document.cookie = `dev_role=${role}; path=/; max-age=86400; samesite=lax`;
    window.location.href = portal;
  };

  return (
    <div className="max-w-md w-full mx-auto space-y-4">
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-amber-800 text-xs font-bold">
        DEMO MODE — Clerk sign-in is not configured yet, so you can enter any portal directly.
        Real logins with passwords take over automatically once Clerk keys are added.
      </div>
      {ROLES.map(({ role, portal, label, desc }) => (
        <button
          key={role}
          type="button"
          disabled={busy !== null}
          onClick={() => enter(role, portal)}
          className="w-full bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition text-left disabled:opacity-60"
        >
          <p className="font-extrabold text-slate-900">
            {busy === role ? "Entering…" : `${label} Portal`}
          </p>
          <p className="text-xs text-slate-500 font-semibold mt-1">{desc}</p>
        </button>
      ))}
      {error && (
        <p className="text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">
          {error}
        </p>
      )}
    </div>
  );
}

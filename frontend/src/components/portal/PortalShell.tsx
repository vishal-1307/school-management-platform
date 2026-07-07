/**
 * Portal chrome: sidebar navigation, topbar, and the client-side auth
 * guard. Every portal page island wraps its content in this component.
 * On mount it fetches /api/auth/me (the authoritative role check); users
 * whose role doesn't match the portal are bounced to their own portal.
 */

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getMe, portalHomeFor, signOut, type Me } from "../../lib/authStore";
import { Spinner, ToastProvider } from "./kit";

interface NavItem {
  label: string;
  href: string;
  icon: string; // emoji keeps the bundle tiny; swap for SVGs later if wanted
}

const NAV: Record<string, NavItem[]> = {
  admin: [
    { label: "Dashboard", href: "/admin", icon: "📊" },
    { label: "Students", href: "/admin/students", icon: "🎓" },
    { label: "Staff", href: "/admin/staff", icon: "👩‍🏫" },
    { label: "Admissions", href: "/admin/admissions", icon: "📝" },
    { label: "Fees", href: "/admin/fees", icon: "💰" },
    { label: "Attendance", href: "/admin/attendance", icon: "🗓️" },
    { label: "Exams & Results", href: "/admin/exams", icon: "🧮" },
    { label: "Timetable", href: "/admin/timetable", icon: "⏰" },
    { label: "Homework", href: "/admin/homework", icon: "📚" },
    { label: "Notices", href: "/admin/notices", icon: "📣" },
    { label: "Website CMS", href: "/admin/cms", icon: "🖼️" },
    { label: "Enquiries Inbox", href: "/admin/messages", icon: "📥" },
    { label: "Reports", href: "/admin/reports", icon: "📈" },
    { label: "Communication Log", href: "/admin/communication", icon: "💬" },
    { label: "Leave Requests", href: "/admin/leaves", icon: "🌴" },
    { label: "Users & Roles", href: "/admin/users", icon: "🔐" },
    { label: "Settings", href: "/admin/settings", icon: "⚙️" },
  ],
  teacher: [
    { label: "Dashboard", href: "/teacher", icon: "📊" },
    { label: "My Timetable", href: "/teacher/timetable", icon: "⏰" },
    { label: "Attendance", href: "/teacher/attendance", icon: "🗓️" },
    { label: "Homework", href: "/teacher/homework", icon: "📚" },
    { label: "Marks Entry", href: "/teacher/marks", icon: "🧮" },
    { label: "My Students", href: "/teacher/students", icon: "🎓" },
    { label: "Notices", href: "/teacher/notices", icon: "📣" },
    { label: "Leave", href: "/teacher/leave", icon: "🌴" },
    { label: "Profile", href: "/teacher/profile", icon: "👤" },
  ],
  student: [
    { label: "Dashboard", href: "/student", icon: "📊" },
    { label: "My Attendance", href: "/student/attendance", icon: "🗓️" },
    { label: "Homework", href: "/student/homework", icon: "📚" },
    { label: "Results", href: "/student/results", icon: "🧮" },
    { label: "Timetable", href: "/student/timetable", icon: "⏰" },
    { label: "Notices", href: "/student/notices", icon: "📣" },
    { label: "Fees", href: "/student/fees", icon: "💰" },
    { label: "Profile", href: "/student/profile", icon: "👤" },
  ],
};

const PORTAL_ROLES: Record<string, string[]> = {
  admin: ["super_admin", "office_admin"],
  teacher: ["teacher"],
  student: ["student", "parent"],
};

const PORTAL_TITLES: Record<string, string> = {
  admin: "Admin Portal",
  teacher: "Teacher Portal",
  student: "Student Portal",
};

export default function PortalShell({
  portal,
  title,
  children,
}: {
  portal: "admin" | "teacher" | "student";
  title: string;
  children: ReactNode | ((me: Me) => ReactNode);
}) {
  const [me, setMe] = useState<Me | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "unauthorized">("loading");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    getMe().then((user) => {
      if (!user) {
        window.location.href = "/sign-in";
        return;
      }
      if (!PORTAL_ROLES[portal].includes(user.role)) {
        window.location.href = portalHomeFor(user.role);
        setState("unauthorized");
        return;
      }
      setMe(user);
      setState("ready");
    });
  }, [portal]);

  if (state !== "ready" || !me) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const nav = NAV[portal];
  const path = typeof location !== "undefined" ? location.pathname.replace(/\/$/, "") : "";

  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-50 flex">
        {/* Sidebar */}
        <aside
          className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-100 flex flex-col transition-transform lg:translate-x-0 ${
            menuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="p-5 border-b border-slate-100">
            <a href="/" className="block">
              <p className="font-heading font-extrabold text-slate-900 leading-tight">
                Knowledge Academy
              </p>
              <p className="text-xs font-bold text-indigo-600">{PORTAL_TITLES[portal]}</p>
            </a>
          </div>
          <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
            {nav.map((item) => {
              const active = path === item.href;
              return (
                <a
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold transition ${
                    active
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <span aria-hidden>{item.icon}</span>
                  {item.label}
                </a>
              );
            })}
          </nav>
          <div className="p-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => signOut()}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold text-slate-600 hover:bg-rose-50 hover:text-rose-700 transition"
            >
              <span aria-hidden>🚪</span> Sign out
            </button>
          </div>
        </aside>

        {menuOpen && (
          <div
            className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
            onClick={() => setMenuOpen(false)}
          />
        )}

        {/* Main */}
        <div className="flex-1 min-w-0 flex flex-col">
          <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-slate-100 px-4 lg:px-8 py-3.5 flex items-center gap-4">
            <button
              type="button"
              className="lg:hidden p-2 rounded-xl hover:bg-slate-100 font-bold"
              onClick={() => setMenuOpen(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <h1 className="text-lg font-extrabold font-heading text-slate-900 truncate">{title}</h1>
            <div className="ml-auto flex items-center gap-3">
              <span className="hidden sm:block text-xs font-bold text-slate-500">
                {me.email || me.role}
              </span>
              <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-bold uppercase tracking-wider">
                {me.role.replace("_", " ")}
              </span>
            </div>
          </header>
          <main className="flex-1 p-4 lg:p-8 space-y-6">
            {typeof children === "function" ? children(me) : children}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}

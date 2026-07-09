/**
 * Portal chrome: sidebar navigation, topbar, and the client-side auth
 * guard. Every portal page island wraps its content in this component.
 * On mount it fetches /api/auth/me (the authoritative role check); users
 * whose role doesn't match the portal are bounced to their own portal.
 */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Award,
  BarChart3,
  BookOpen,
  CalendarCheck,
  CalendarOff,
  ChevronDown,
  ClipboardList,
  Clock,
  GraduationCap,
  Image as ImageIcon,
  Inbox,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Megaphone,
  MessageSquare,
  Menu,
  Settings,
  User as UserIcon,
  Users,
  Wallet,
  X,
  type LucideIcon,
} from "lucide-react";
import { getMe, portalHomeFor, signOut, type Me } from "../../lib/authStore";
import { useIdleTimeout } from "../../lib/useIdleTimeout";
import { Button, Modal, Spinner, ToastProvider } from "./kit";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface NavGroup {
  label: string | null;
  items: NavItem[];
}

const ADMIN_NAV: NavGroup[] = [
  { label: "OVERVIEW", items: [{ label: "Dashboard", href: "/admin", icon: LayoutDashboard }] },
  {
    label: "ACADEMICS",
    items: [
      { label: "Students", href: "/admin/students", icon: GraduationCap },
      { label: "Staff", href: "/admin/staff", icon: Users },
      { label: "Attendance", href: "/admin/attendance", icon: CalendarCheck },
      { label: "Exams & Results", href: "/admin/exams", icon: Award },
      { label: "Timetable", href: "/admin/timetable", icon: Clock },
      { label: "Homework", href: "/admin/homework", icon: BookOpen },
    ],
  },
  {
    label: "ADMISSIONS & FEES",
    items: [
      { label: "Admissions", href: "/admin/admissions", icon: ClipboardList },
      { label: "Fees", href: "/admin/fees", icon: Wallet },
    ],
  },
  {
    label: "COMMUNICATION",
    items: [
      { label: "Notices", href: "/admin/notices", icon: Megaphone },
      { label: "Website CMS", href: "/admin/cms", icon: ImageIcon },
      { label: "Enquiries Inbox", href: "/admin/messages", icon: Inbox },
      { label: "Communication Log", href: "/admin/communication", icon: MessageSquare },
    ],
  },
  {
    label: "SYSTEM",
    items: [
      { label: "Reports", href: "/admin/reports", icon: BarChart3 },
      { label: "Leave Requests", href: "/admin/leaves", icon: CalendarOff },
      { label: "Users & Roles", href: "/admin/users", icon: KeyRound },
      { label: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
];

const TEACHER_NAV: NavGroup[] = [
  {
    label: null,
    items: [
      { label: "Dashboard", href: "/teacher", icon: LayoutDashboard },
      { label: "My Timetable", href: "/teacher/timetable", icon: Clock },
      { label: "Attendance", href: "/teacher/attendance", icon: CalendarCheck },
      { label: "Homework", href: "/teacher/homework", icon: BookOpen },
      { label: "Marks Entry", href: "/teacher/marks", icon: Award },
      { label: "My Students", href: "/teacher/students", icon: GraduationCap },
      { label: "Notices", href: "/teacher/notices", icon: Megaphone },
      { label: "Leave", href: "/teacher/leave", icon: CalendarOff },
      { label: "Profile", href: "/teacher/profile", icon: UserIcon },
    ],
  },
];

const STUDENT_NAV: NavGroup[] = [
  {
    label: null,
    items: [
      { label: "Dashboard", href: "/student", icon: LayoutDashboard },
      { label: "My Attendance", href: "/student/attendance", icon: CalendarCheck },
      { label: "Homework", href: "/student/homework", icon: BookOpen },
      { label: "Results", href: "/student/results", icon: Award },
      { label: "Timetable", href: "/student/timetable", icon: Clock },
      { label: "Notices", href: "/student/notices", icon: Megaphone },
      { label: "Fees", href: "/student/fees", icon: Wallet },
      { label: "Profile", href: "/student/profile", icon: UserIcon },
    ],
  },
];

const NAV: Record<string, NavGroup[]> = {
  admin: ADMIN_NAV,
  teacher: TEACHER_NAV,
  student: STUDENT_NAV,
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

const PROFILE_HREF: Record<string, string> = {
  admin: "/admin/settings",
  teacher: "/teacher/profile",
  student: "/student/profile",
};

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function ProfileMenu({ me, portal }: { me: Me; portal: "admin" | "teacher" | "student" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const roleLabel = me.role.replace("_", " ").toUpperCase();

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 pl-1 pr-2.5 py-1 rounded-full hover:bg-slate-100 transition"
      >
        <span className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-extrabold flex-shrink-0">
          {initialsOf(me.display_name || me.login_id)}
        </span>
        <span className="hidden sm:flex flex-col items-start leading-tight">
          <span className="text-xs font-bold text-slate-700">{me.login_id}</span>
          <span className="text-[10px] font-bold text-indigo-600 tracking-wider">{roleLabel}</span>
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-2xl border border-slate-100 shadow-lg py-2 z-50">
          <div className="px-4 py-3 border-b border-slate-50">
            <p className="font-extrabold text-slate-900 text-sm">{me.display_name || me.login_id}</p>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mt-0.5">{roleLabel}</p>
            <p className="text-xs text-slate-500 font-semibold mt-1">ID: {me.login_id}</p>
            {me.class_label && (
              <p className="text-xs text-slate-500 font-semibold">{me.class_label}</p>
            )}
          </div>
          <a
            href={PROFILE_HREF[portal]}
            className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            <KeyRound className="w-4 h-4" /> Change Password
          </a>
          <button
            type="button"
            onClick={() => signOut()}
            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-bold text-rose-600 hover:bg-rose-50"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      )}
    </div>
  );
}

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
  const idle = useIdleTimeout();

  useEffect(() => {
    getMe().then((user) => {
      if (!user) {
        window.location.href = "/login";
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

  useEffect(() => {
    // Cache-Control: no-store stops HTTP caching, but the back-forward
    // cache restores pages from memory without any request. If this DOM is
    // resurrected that way, re-validate the session before showing it.
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        getMe(true).then((user) => {
          if (!user) window.location.replace("/login");
        });
      }
    };
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, []);

  if (state !== "ready" || !me) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const groups = NAV[portal];
  const path = typeof location !== "undefined" ? location.pathname.replace(/\/$/, "") : "";

  return (
    <ToastProvider>
      <Modal title="Are you still there?" open={idle.warning} onClose={idle.staySignedIn}>
        <div className="space-y-4">
          <p className="text-sm font-semibold text-slate-600">
            You&apos;ll be signed out soon due to inactivity — in about{" "}
            <span className="font-extrabold text-slate-900">{idle.secondsLeft}s</span>.
          </p>
          <Button onClick={idle.staySignedIn}>Stay signed in</Button>
        </div>
      </Modal>
      <div className="min-h-screen bg-slate-50 flex">
        {/* Sidebar */}
        <aside
          className={`fixed lg:static inset-y-0 left-0 z-40 w-[260px] bg-slate-900 flex flex-col transition-transform lg:translate-x-0 ${
            menuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <a href="/" className="block">
              <p className="font-heading font-extrabold text-white leading-tight">
                Knowledge Academy
              </p>
              <p className="text-xs font-bold text-indigo-400">{PORTAL_TITLES[portal]}</p>
            </a>
            <button
              type="button"
              className="lg:hidden p-1.5 rounded-lg hover:bg-slate-800 text-slate-400"
              onClick={() => setMenuOpen(false)}
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto p-3 space-y-4">
            {groups.map((group, gi) => (
              <div key={group.label ?? gi} className="space-y-0.5">
                {group.label && (
                  <p className="px-3 pt-2 pb-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">
                    {group.label}
                  </p>
                )}
                {group.items.map((item) => {
                  const active = path === item.href;
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold transition ${
                        active
                          ? "bg-indigo-600 text-white"
                          : "text-slate-300 hover:bg-slate-800 hover:text-white"
                      }`}
                    >
                      <Icon className="w-[18px] h-[18px] flex-shrink-0" />
                      {item.label}
                    </a>
                  );
                })}
              </div>
            ))}
          </nav>
          <div className="p-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => signOut()}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold text-slate-300 hover:bg-rose-950 hover:text-rose-300 transition"
            >
              <LogOut className="w-[18px] h-[18px]" /> Sign out
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
          <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-slate-100 px-4 lg:px-8 py-3 flex items-center gap-4">
            <button
              type="button"
              className="lg:hidden p-2 rounded-xl hover:bg-slate-100 text-slate-600"
              onClick={() => setMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-extrabold font-heading text-slate-900 truncate">{title}</h1>
            <div className="ml-auto flex items-center gap-3">
              <ProfileMenu me={me} portal={portal} />
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

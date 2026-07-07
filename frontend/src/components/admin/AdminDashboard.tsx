import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { StatCard } from "../portal/kit";

interface Stats {
  students: number | null;
  staff: number | null;
  enquiries: number | null;
  feesCollected: number | null;
  feesPending: number | null;
}

const QUICK_ACTIONS = [
  { label: "Add Student", href: "/admin/students", icon: "🎓" },
  { label: "Mark / Fix Attendance", href: "/admin/attendance", icon: "🗓️" },
  { label: "Send Notice", href: "/admin/notices", icon: "📣" },
  { label: "Record Fee Payment", href: "/admin/fees", icon: "💰" },
];

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    students: null,
    staff: null,
    enquiries: null,
    feesCollected: null,
    feesPending: null,
  });

  useEffect(() => {
    authFetch<{ total: number }>("/api/students/?page_size=1")
      .then((data) => setStats((s) => ({ ...s, students: data.total })))
      .catch(() => {});
    authFetch<unknown[]>("/api/staff/")
      .then((data) => setStats((s) => ({ ...s, staff: data.length })))
      .catch(() => {});
    authFetch<{ total_enquiries?: number; total?: number }>("/api/reports/admission-funnel")
      .then((data) =>
        setStats((s) => ({ ...s, enquiries: data.total_enquiries ?? data.total ?? 0 })),
      )
      .catch(() => {});
    authFetch<{ total_collected?: number; total_pending?: number }>(
      "/api/reports/fee-collection-summary",
    )
      .then((data) =>
        setStats((s) => ({
          ...s,
          feesCollected: data.total_collected ?? 0,
          feesPending: data.total_pending ?? 0,
        })),
      )
      .catch(() => {});
  }, []);

  const rupees = (value: number | null) =>
    value === null ? "…" : `₹${value.toLocaleString("en-IN")}`;

  return (
    <PortalShell portal="admin" title="Dashboard">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Students" value={stats.students ?? "…"} />
        <StatCard label="Total Staff" value={stats.staff ?? "…"} tone="emerald" />
        <StatCard label="Admission Enquiries" value={stats.enquiries ?? "…"} tone="amber" />
        <StatCard label="Fees Collected" value={rupees(stats.feesCollected)} tone="emerald" hint={`Pending: ${rupees(stats.feesPending)}`} />
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Quick actions</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {QUICK_ACTIONS.map((action) => (
            <a
              key={action.href}
              href={action.href}
              className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition font-bold text-slate-800 flex items-center gap-3"
            >
              <span className="text-2xl" aria-hidden>{action.icon}</span>
              {action.label}
            </a>
          ))}
        </div>
      </section>
    </PortalShell>
  );
}

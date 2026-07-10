import { useEffect, useState } from "react";
import {
  CalendarCheck,
  ClipboardList,
  GraduationCap,
  Inbox,
  Megaphone,
  UserPlus,
  Users,
  Wallet,
} from "lucide-react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { AreaTrend, HorizontalBars, TrendBadge } from "../portal/charts";
import { ErrorNote, Spinner } from "../portal/kit";

interface KpiValue {
  value: number;
  trend_percent: number | null;
}

interface MonthlyPoint {
  month: string;
  label: string;
  amount: number;
}

interface ClassAttendanceBar {
  class_name: string;
  percentage: number;
}

interface ActivityItem {
  type: "notice" | "enquiry" | "payment";
  text: string;
  at: string;
}

interface AdminDashboard {
  total_students: KpiValue;
  total_staff: KpiValue;
  fees_collected: KpiValue;
  fees_pending: number;
  new_enquiries: number;
  fee_collection_by_month: MonthlyPoint[];
  attendance_by_class: ClassAttendanceBar[];
  recent_activity: ActivityItem[];
  generated_at: string;
}

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const ACTIVITY_ICON: Record<ActivityItem["type"], React.ReactNode> = {
  notice: <Megaphone className="w-4 h-4 text-indigo-600" />,
  enquiry: <UserPlus className="w-4 h-4 text-amber-600" />,
  payment: <Wallet className="w-4 h-4 text-emerald-600" />,
};

const QUICK_ACTIONS = [
  { label: "Add Student", href: "/admin/students", icon: GraduationCap },
  { label: "Mark Attendance", href: "/admin/attendance", icon: CalendarCheck },
  { label: "Send Notice", href: "/admin/notices", icon: Megaphone },
  { label: "Record Payment", href: "/admin/fees", icon: Wallet },
];

function DashboardBody() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    authFetch<AdminDashboard>("/api/reports/dashboard-summary")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!data) return <Spinner />;

  return (
    <>
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Students</p>
            <GraduationCap className="w-4 h-4 text-slate-300" />
          </div>
          <p className="text-2xl font-extrabold font-heading text-slate-800">
            {data.total_students.value.toLocaleString("en-IN")}
          </p>
          <TrendBadge percent={data.total_students.trend_percent} />
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Staff</p>
            <Users className="w-4 h-4 text-slate-300" />
          </div>
          <p className="text-2xl font-extrabold font-heading text-slate-800">
            {data.total_staff.value.toLocaleString("en-IN")}
          </p>
          <TrendBadge percent={data.total_staff.trend_percent} />
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Fees Collected</p>
            <Wallet className="w-4 h-4 text-slate-300" />
          </div>
          <p className="text-2xl font-extrabold font-heading text-emerald-600">
            {rupees(data.fees_collected.value)}
          </p>
          <div className="flex items-center gap-2">
            <TrendBadge percent={data.fees_collected.trend_percent} />
            <span className="text-xs font-bold text-rose-600">Pending: {rupees(data.fees_pending)}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">New Enquiries</p>
            <span className="relative">
              <Inbox className="w-4 h-4 text-slate-300" />
              {data.new_enquiries > 0 && (
                <span
                  aria-hidden="true"
                  className="absolute -top-1 -right-1 w-2 h-2 bg-rose-500 rounded-full"
                />
              )}
            </span>
          </div>
          <p className="text-2xl font-extrabold font-heading text-slate-800">{data.new_enquiries}</p>
          <a href="/admin/admissions" className="text-xs font-bold text-indigo-600 hover:underline">
            View pipeline →
          </a>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
          <h2 className="font-extrabold text-slate-800">Fee Collection — Last 6 Months</h2>
          <AreaTrend points={data.fee_collection_by_month.map((p) => ({ label: p.label, amount: p.amount }))} />
        </section>

        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
          <h2 className="font-extrabold text-slate-800">Attendance by Class — This Week</h2>
          <HorizontalBars
            data={data.attendance_by_class.map((c) => ({ label: c.class_name, percentage: c.percentage }))}
          />
        </section>
      </div>

      {/* Recent activity + quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
          <h2 className="font-extrabold text-slate-800 flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-indigo-600" /> Recent Activity
          </h2>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-slate-400 font-semibold py-4">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-slate-50">
              {data.recent_activity.map((item, i) => (
                <li key={i} className="flex items-start gap-3 py-2.5">
                  <span className="mt-0.5">{ACTIVITY_ICON[item.type]}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-700">{item.text}</p>
                    <p className="text-xs text-slate-400 font-semibold">{timeAgo(item.at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Quick Actions</h2>
          <div className="grid grid-cols-1 gap-3">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <a
                  key={action.href}
                  href={action.href}
                  className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition font-bold text-slate-800 flex items-center gap-3"
                >
                  <Icon className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                  {action.label}
                </a>
              );
            })}
          </div>
        </section>
      </div>

      <p className="text-xs text-slate-400 font-semibold text-right">
        Updated {timeAgo(data.generated_at)}
      </p>
    </>
  );
}

export default function AdminDashboard() {
  return (
    <PortalShell portal="admin" title="Dashboard">
      <DashboardBody />
    </PortalShell>
  );
}

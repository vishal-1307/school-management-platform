import { useEffect, useState } from "react";
import { BookOpen, Calendar, Megaphone, Wallet } from "lucide-react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { RingGauge } from "../portal/charts";
import { ErrorNote, Spinner } from "../portal/kit";

interface TimetablePeriod {
  period_number: number;
  subject_name: string;
  subtitle: string;
  is_current: boolean;
}

interface LatestResult {
  exam_name: string;
  published: boolean;
  percentage: number | null;
  grade: string | null;
}

interface DashboardNotice {
  id: number;
  title: string;
  published_at: string | null;
}

interface StudentDashboard {
  attendance_percentage: number | null;
  pending_homework_count: number;
  latest_result: LatestResult | null;
  fee_due: number;
  today_timetable: TimetablePeriod[];
  recent_notices: DashboardNotice[];
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

function DashboardBody() {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    authFetch<StudentDashboard>("/api/students/me/dashboard")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!data) return <Spinner />;

  const homeworkTone = data.pending_homework_count > 0 ? "amber" : "emerald";
  const feeTone = data.fee_due > 0 ? "rose" : "emerald";

  return (
    <>
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex flex-col sm:flex-row items-center gap-3 sm:gap-4 text-center sm:text-left">
          <span className="sm:hidden">
            <RingGauge percentage={data.attendance_percentage} size={56} strokeWidth={7} />
          </span>
          <span className="hidden sm:block">
            <RingGauge percentage={data.attendance_percentage} size={72} strokeWidth={8} />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Attendance</p>
            <p className="text-xs text-slate-500 font-semibold mt-1">
              {data.attendance_percentage === null ? "No records yet" : "This year"}
            </p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Pending Homework</p>
            <BookOpen className="w-4 h-4 text-slate-300" />
          </div>
          <p
            className={`inline-block px-3 py-1 rounded-xl text-2xl font-extrabold font-heading ${
              homeworkTone === "amber" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {data.pending_homework_count}
          </p>
          <p className="text-xs text-slate-500 font-semibold">
            {data.pending_homework_count > 0 ? "Not yet submitted" : "All caught up"}
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Latest Result</p>
          {data.latest_result ? (
            <>
              <p className="text-2xl font-extrabold font-heading text-slate-800">
                {data.latest_result.percentage}%
              </p>
              <p className="text-xs text-slate-500 font-semibold truncate">
                {data.latest_result.exam_name} · Grade {data.latest_result.grade}
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-bold text-slate-400">No results published yet</p>
              <p className="text-xs text-slate-400 font-semibold">Check back after exams</p>
            </>
          )}
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Fee Due</p>
            <Wallet className="w-4 h-4 text-slate-300" />
          </div>
          <p
            className={`text-2xl font-extrabold font-heading ${
              feeTone === "rose" ? "text-rose-600" : "text-emerald-600"
            }`}
          >
            {rupees(data.fee_due)}
          </p>
          {data.fee_due > 0 ? (
            <a
              href="/student/fees"
              className="inline-block px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition"
            >
              Pay Now
            </a>
          ) : (
            <p className="text-xs text-emerald-600 font-semibold">Fully paid</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Today's timetable */}
        <section className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
          <h2 className="font-extrabold text-slate-800 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-600" /> Today's Timetable
          </h2>
          {data.today_timetable.length === 0 ? (
            <p className="text-sm text-slate-400 font-semibold py-4">No periods scheduled today.</p>
          ) : (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {data.today_timetable.map((period) => (
                <div
                  key={period.period_number}
                  className={`flex-shrink-0 w-32 rounded-xl p-3 border ${
                    period.is_current
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "bg-slate-50 border-slate-100 text-slate-700"
                  }`}
                >
                  <p className={`text-[10px] font-bold uppercase ${period.is_current ? "text-indigo-200" : "text-slate-400"}`}>
                    Period {period.period_number}
                  </p>
                  <p className="font-extrabold text-sm mt-1 truncate">{period.subject_name}</p>
                  <p className={`text-xs font-semibold truncate ${period.is_current ? "text-indigo-100" : "text-slate-500"}`}>
                    {period.subtitle}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Recent notices */}
        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
          <h2 className="font-extrabold text-slate-800 flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-indigo-600" /> Recent Notices
          </h2>
          {data.recent_notices.length === 0 ? (
            <p className="text-sm text-slate-400 font-semibold py-4">No notices yet.</p>
          ) : (
            <ul className="space-y-2.5">
              {data.recent_notices.map((notice) => (
                <li key={notice.id} className="text-sm">
                  <a href="/student/notices" className="font-bold text-slate-700 hover:text-indigo-600">
                    {notice.title}
                  </a>
                  {notice.published_at && (
                    <p className="text-xs text-slate-400 font-semibold">{timeAgo(notice.published_at)}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="text-xs text-slate-400 font-semibold text-right">
        Updated {timeAgo(data.generated_at)}
      </p>
    </>
  );
}

export default function StudentDashboard() {
  return (
    <PortalShell portal="student" title="Dashboard">
      {(me) => (
        <>
          <p className="text-slate-500 font-semibold">
            Hi, {(me.display_name || me.login_id).split(" ")[0]}
            {me.class_label ? ` · ${me.class_label}` : ""}
          </p>
          <DashboardBody />
        </>
      )}
    </PortalShell>
  );
}

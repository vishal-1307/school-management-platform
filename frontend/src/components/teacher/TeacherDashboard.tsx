import { useEffect, useState } from "react";
import { CalendarCheck, ClipboardCheck, Megaphone, Users } from "lucide-react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { DataTable, ErrorNote, Spinner, type Column } from "../portal/kit";

interface TimetablePeriod {
  period_number: number;
  subject_name: string;
  subtitle: string;
  is_current: boolean;
}

interface ClassSectionRef {
  class_id: number;
  section_id: number;
  class_name: string;
  section_name: string;
}

interface AttendanceStatus {
  all_marked: boolean;
  pending: ClassSectionRef[];
}

interface MyClassChip {
  class_name: string;
  section_name: string;
  subject_name: string;
}

interface PendingMarksRow {
  exam_id: number;
  exam_subject_id: number;
  exam_name: string;
  subject_name: string;
  class_name: string;
  entered_count: number;
  total_students: number;
}

interface DashboardNotice {
  id: number;
  title: string;
  published_at: string | null;
}

interface TeacherDashboard {
  today_schedule: TimetablePeriod[];
  attendance_status: AttendanceStatus;
  homework_to_review_count: number;
  my_classes: MyClassChip[];
  latest_notice: DashboardNotice | null;
  pending_marks: PendingMarksRow[];
  generated_at: string;
}

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
  const [data, setData] = useState<TeacherDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    authFetch<TeacherDashboard>("/api/staff/me/dashboard")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!data) return <Spinner />;

  const columns: Column<PendingMarksRow>[] = [
    { header: "Exam", render: (r) => r.exam_name },
    { header: "Subject", render: (r) => r.subject_name },
    { header: "Class", render: (r) => r.class_name },
    { header: "Progress", render: (r) => `${r.entered_count} / ${r.total_students} entered` },
    {
      header: "Action",
      render: (r) => (
        <a
          href="/teacher/marks"
          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition inline-block"
        >
          Enter Marks
        </a>
      ),
    },
  ];

  return (
    <>
      {/* Today's schedule hero strip */}
      <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
        <h2 className="font-extrabold text-slate-800">Today's Schedule</h2>
        {data.today_schedule.length === 0 ? (
          <p className="text-sm text-slate-400 font-semibold py-2">No periods scheduled today.</p>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {data.today_schedule.map((period) => (
              <div
                key={period.period_number}
                className={`flex-shrink-0 w-36 rounded-xl p-3 border ${
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

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Mark Attendance</p>
            <CalendarCheck className="w-4 h-4 text-slate-300" />
          </div>
          {data.attendance_status.all_marked ? (
            <p className="inline-block px-3 py-1 rounded-xl text-lg font-extrabold font-heading bg-emerald-50 text-emerald-700">
              Done
            </p>
          ) : (
            <>
              <p className="inline-block px-3 py-1 rounded-xl text-lg font-extrabold font-heading bg-amber-50 text-amber-700">
                Pending
              </p>
              <p className="text-xs text-slate-500 font-semibold truncate">
                {data.attendance_status.pending
                  .map((p) => `${p.class_name} ${p.section_name}`)
                  .join(", ")}
              </p>
              <a href="/teacher/attendance" className="text-xs font-bold text-indigo-600 hover:underline">
                Mark now →
              </a>
            </>
          )}
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Homework to Review</p>
            <ClipboardCheck className="w-4 h-4 text-slate-300" />
          </div>
          <p
            className={`inline-block px-3 py-1 rounded-xl text-2xl font-extrabold font-heading ${
              data.homework_to_review_count > 0 ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {data.homework_to_review_count}
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">My Classes</p>
            <Users className="w-4 h-4 text-slate-300" />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.my_classes.length === 0 ? (
              <p className="text-xs text-slate-400 font-semibold">No assignments yet</p>
            ) : (
              data.my_classes.map((c, i) => (
                <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-[11px] font-bold">
                  {c.class_name} {c.section_name} · {c.subject_name}
                </span>
              ))
            )}
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Latest Notice</p>
            <Megaphone className="w-4 h-4 text-slate-300" />
          </div>
          {data.latest_notice ? (
            <>
              <p className="font-bold text-sm text-slate-700 truncate">{data.latest_notice.title}</p>
              {data.latest_notice.published_at && (
                <p className="text-xs text-slate-400 font-semibold">{timeAgo(data.latest_notice.published_at)}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-400 font-semibold">No notices yet</p>
          )}
        </div>
      </div>

      {/* Pending marks entry */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Pending Marks Entry</h2>
        <DataTable
          columns={columns}
          rows={data.pending_marks}
          keyFor={(r) => r.exam_subject_id}
          empty="Nothing pending — all your marks are entered."
        />
      </section>

      <p className="text-xs text-slate-400 font-semibold text-right">
        Updated {timeAgo(data.generated_at)}
      </p>
    </>
  );
}

export default function TeacherDashboard() {
  return (
    <PortalShell portal="teacher" title="Dashboard">
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

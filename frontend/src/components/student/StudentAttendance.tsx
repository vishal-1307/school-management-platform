import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Spinner, StatCard, formatDate } from "../portal/kit";

interface MyAttendance {
  records: { date: string; status: string; period: number | null }[];
  present: number;
  absent: number;
  late: number;
  percentage: number | null;
}

const STATUS_TONES: Record<string, string> = {
  present: "bg-emerald-50 text-emerald-700",
  absent: "bg-rose-50 text-rose-700",
  late: "bg-amber-50 text-amber-700",
};

function AttendanceView() {
  const [data, setData] = useState<MyAttendance | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    authFetch<MyAttendance>("/api/attendance/my")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load attendance"));
  }, []);

  if (error)
    return <p className="text-sm font-semibold text-rose-700 bg-rose-50 rounded-xl px-4 py-3">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Attendance %"
          value={data.percentage !== null ? `${data.percentage}%` : "—"}
          tone={data.percentage !== null && data.percentage < 75 ? "rose" : "emerald"}
          hint={data.percentage !== null && data.percentage < 75 ? "Below the 75% requirement" : undefined}
        />
        <StatCard label="Present" value={data.present} tone="emerald" />
        <StatCard label="Absent" value={data.absent} tone="rose" />
        <StatCard label="Late" value={data.late} tone="amber" />
      </div>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50 max-h-[520px] overflow-y-auto">
        {data.records.length === 0 && (
          <p className="px-4 py-8 text-sm text-slate-400 font-semibold">No attendance recorded yet.</p>
        )}
        {data.records.map((record, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-2.5 text-sm font-semibold">
            <span className="flex-1 text-slate-700">{formatDate(record.date)}</span>
            {record.period !== null && <span className="text-xs text-slate-400">Period {record.period}</span>}
            <span
              className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold uppercase ${STATUS_TONES[record.status]}`}
            >
              {record.status}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

export default function StudentAttendance() {
  return (
    <PortalShell portal="student" title="My Attendance">
      <AttendanceView />
    </PortalShell>
  );
}

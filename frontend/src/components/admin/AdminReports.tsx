import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Spinner, StatCard } from "../portal/kit";

interface TrendPoint {
  date: string;
  present: number;
  absent: number;
  late?: number;
}

interface FeeSummary {
  total_expected?: number;
  total_collected?: number;
  total_pending?: number;
  by_head?: { fee_head: string; expected: number; collected: number }[];
}

interface Funnel {
  [status: string]: number | string;
}

const rupees = (value?: number) => (value === undefined ? "…" : `₹${value.toLocaleString("en-IN")}`);

function Bar({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const width = max > 0 ? Math.max(2, (value / max) * 100) : 2;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-bold text-slate-600">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function ReportsPage() {
  const [trends, setTrends] = useState<TrendPoint[] | null>(null);
  const [fees, setFees] = useState<FeeSummary | null>(null);
  const [funnel, setFunnel] = useState<Funnel | null>(null);

  useEffect(() => {
    authFetch<{ data: TrendPoint[] }>("/api/reports/attendance-trends")
      .then((r) => setTrends(r.data))
      .catch(() => setTrends([]));
    authFetch<FeeSummary>("/api/reports/fee-collection-summary")
      .then(setFees)
      .catch(() => setFees({}));
    authFetch<Funnel>("/api/reports/admission-funnel")
      .then(setFunnel)
      .catch(() => setFunnel({}));
  }, []);

  if (!trends || !fees || !funnel) return <Spinner />;

  const maxAttendance = Math.max(1, ...trends.map((t) => t.present + t.absent + (t.late ?? 0)));
  const funnelEntries = Object.entries(funnel).filter(
    ([key, value]) => typeof value === "number" && key !== "conversion_rate",
  ) as [string, number][];
  const maxFunnel = Math.max(1, ...funnelEntries.map(([, v]) => v));

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Fees Expected" value={rupees(fees.total_expected)} />
        <StatCard label="Fees Collected" value={rupees(fees.total_collected)} tone="emerald" />
        <StatCard label="Fees Pending" value={rupees(fees.total_pending)} tone="rose" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
          <h2 className="font-extrabold text-slate-800">Attendance — last days</h2>
          {trends.length === 0 ? (
            <p className="text-sm text-slate-400 font-semibold">No attendance recorded yet.</p>
          ) : (
            trends.slice(-10).map((point) => (
              <div key={point.date} className="space-y-1">
                <p className="text-xs font-bold text-slate-400">{point.date}</p>
                <div className="flex h-3 rounded-full overflow-hidden bg-slate-100">
                  <div
                    className="bg-emerald-500"
                    style={{ width: `${(point.present / maxAttendance) * 100}%` }}
                    title={`Present ${point.present}`}
                  />
                  <div
                    className="bg-rose-500"
                    style={{ width: `${(point.absent / maxAttendance) * 100}%` }}
                    title={`Absent ${point.absent}`}
                  />
                  {point.late ? (
                    <div
                      className="bg-amber-400"
                      style={{ width: `${(point.late / maxAttendance) * 100}%` }}
                      title={`Late ${point.late}`}
                    />
                  ) : null}
                </div>
              </div>
            ))
          )}
          <p className="text-[10px] font-bold text-slate-400">
            <span className="text-emerald-600">■ Present</span>{" "}
            <span className="text-rose-600">■ Absent</span>{" "}
            <span className="text-amber-500">■ Late</span>
          </p>
        </section>

        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
          <h2 className="font-extrabold text-slate-800">Admission funnel</h2>
          {funnelEntries.length === 0 ? (
            <p className="text-sm text-slate-400 font-semibold">No enquiries yet.</p>
          ) : (
            funnelEntries.map(([status, count]) => (
              <Bar
                key={status}
                label={status.replace(/_/g, " ")}
                value={count}
                max={maxFunnel}
                tone="bg-indigo-500"
              />
            ))
          )}
          {"conversion_rate" in funnel && (
            <p className="text-sm font-bold text-slate-600">
              Conversion rate: <span className="text-indigo-600">{String(funnel.conversion_rate)}%</span>
            </p>
          )}
        </section>
      </div>

      {fees.by_head && fees.by_head.length > 0 && (
        <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
          <h2 className="font-extrabold text-slate-800">Collection by fee head</h2>
          {fees.by_head.map((head) => (
            <Bar
              key={head.fee_head}
              label={`${head.fee_head} — collected ${rupees(head.collected)} of ${rupees(head.expected)}`}
              value={head.collected}
              max={Math.max(1, head.expected)}
              tone="bg-emerald-500"
            />
          ))}
        </section>
      )}
    </>
  );
}

export default function AdminReports() {
  return (
    <PortalShell portal="admin" title="Reports & Analytics">
      <ReportsPage />
    </PortalShell>
  );
}

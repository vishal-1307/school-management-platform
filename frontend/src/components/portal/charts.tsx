/**
 * Lightweight dashboard chart primitives — no charting library dependency.
 *
 * Color follows the app's existing brand (indigo primary, emerald/amber/
 * rose status) rather than a generic palette, per the data-viz method's
 * own guidance to substitute brand values. Status color is always paired
 * with a text label, never color alone. Single-series charts carry no
 * legend (the card title already names the series). Low cardinality here
 * (≤10 bars, 6 months) gets direct value labels instead of a hover-only
 * disclosure; native <title> tooltips give free, zero-JS hover detail.
 */

/* ── RingGauge — attendance % ─────────────────────────────────────── */

export function RingGauge({
  percentage,
  size = 96,
  strokeWidth = 10,
}: {
  percentage: number | null;
  size?: number;
  strokeWidth?: number;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const value = percentage ?? 0;
  const offset = circumference * (1 - value / 100);

  const tone =
    percentage === null
      ? "#cbd5e1" // slate-300 — no data yet
      : percentage >= 75
        ? "#059669" // emerald-600 — good
        : percentage >= 60
          ? "#d97706" // amber-600 — warning
          : "#e11d48"; // rose-600 — critical

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={tone}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-extrabold font-heading text-slate-800">
          {percentage === null ? "—" : `${percentage}%`}
        </span>
      </span>
    </div>
  );
}

/* ── AreaTrend — fee collection, last 6 months ───────────────────── */

interface TrendPoint {
  label: string;
  amount: number;
}

export function AreaTrend({ points, height = 160 }: { points: TrendPoint[]; height?: number }) {
  if (points.length === 0) {
    return <p className="text-sm text-slate-400 font-semibold py-8 text-center">No data yet.</p>;
  }
  const width = 560;
  const padding = 28;
  const max = Math.max(...points.map((p) => p.amount), 1);
  const stepX = (width - padding * 2) / Math.max(1, points.length - 1);

  const coords = points.map((p, i) => ({
    x: padding + i * stepX,
    y: height - padding - (p.amount / max) * (height - padding * 2 - 16),
    ...p,
  }));

  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`).join(" ");
  const areaPath =
    `M${coords[0].x},${height - padding} ` +
    coords.map((c) => `L${c.x},${c.y}`).join(" ") +
    ` L${coords[coords.length - 1].x},${height - padding} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }} role="img">
      <defs>
        <linearGradient id="feeTrendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4F46E5" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#4F46E5" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* baseline */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#e2e8f0" strokeWidth={1} />
      <path d={areaPath} fill="url(#feeTrendFill)" />
      <path d={linePath} fill="none" stroke="#4F46E5" strokeWidth={2} />
      {coords.map((c) => (
        <g key={c.label}>
          <circle cx={c.x} cy={c.y} r={4} fill="#4F46E5" stroke="#fff" strokeWidth={1.5}>
            <title>{`${c.label}: ₹${c.amount.toLocaleString("en-IN")}`}</title>
          </circle>
          <text x={c.x} y={height - padding + 16} textAnchor="middle" className="fill-slate-400 text-[10px] font-bold">
            {c.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/* ── HorizontalBars — attendance by class ────────────────────────── */

interface BarDatum {
  label: string;
  percentage: number;
}

export function HorizontalBars({ data }: { data: BarDatum[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-400 font-semibold py-8 text-center">No attendance recorded this week yet.</p>;
  }
  return (
    <div className="space-y-3">
      {data.map((d) => {
        const tone = d.percentage >= 75 ? "bg-emerald-500" : d.percentage >= 60 ? "bg-amber-500" : "bg-rose-500";
        return (
          <div key={d.label} className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-slate-600">
              <span>{d.label}</span>
              <span>{d.percentage}%</span>
            </div>
            <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden" title={`${d.label}: ${d.percentage}%`}>
              <div
                className={`h-full rounded-full ${tone}`}
                style={{ width: `${Math.max(2, d.percentage)}%`, transition: "width 0.4s ease" }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── TrendBadge — small ↑/↓ % indicator next to a KPI ────────────── */

export function TrendBadge({ percent }: { percent: number | null }) {
  if (percent === null) return null;
  const up = percent >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-[11px] font-bold ${up ? "text-emerald-600" : "text-rose-600"}`}
    >
      {up ? "▲" : "▼"} {Math.abs(percent)}%
    </span>
  );
}

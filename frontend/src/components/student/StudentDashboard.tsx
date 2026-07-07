import PortalShell from "../portal/PortalShell";

const SHORTCUTS = [
  { label: "My Attendance", href: "/student/attendance", icon: "🗓️", desc: "Day-wise history and percentage" },
  { label: "Homework", href: "/student/homework", icon: "📚", desc: "What's due and submit your work" },
  { label: "Results", href: "/student/results", icon: "🧮", desc: "Marks and report card, once published" },
  { label: "Fee Status", href: "/student/fees", icon: "💰", desc: "Dues, receipts, and Pay Now" },
];

export default function StudentDashboard() {
  return (
    <PortalShell portal="student" title="Dashboard">
      <p className="text-slate-500 font-semibold">
        Welcome! Parents can use this same login to follow attendance, homework, results, and fees.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {SHORTCUTS.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition space-y-1.5"
          >
            <p className="font-extrabold text-slate-800 flex items-center gap-2">
              <span className="text-xl" aria-hidden>{item.icon}</span> {item.label}
            </p>
            <p className="text-xs text-slate-500 font-semibold">{item.desc}</p>
          </a>
        ))}
      </div>
    </PortalShell>
  );
}

import PortalShell from "../portal/PortalShell";

const SHORTCUTS = [
  { label: "Mark Attendance", href: "/teacher/attendance", icon: "🗓️", desc: "Take today's attendance for your class" },
  { label: "Post Homework", href: "/teacher/homework", icon: "📚", desc: "Assign work visible instantly to students" },
  { label: "Enter Marks", href: "/teacher/marks", icon: "🧮", desc: "Enter exam marks for your subjects" },
  { label: "My Timetable", href: "/teacher/timetable", icon: "⏰", desc: "Your weekly period schedule" },
];

export default function TeacherDashboard() {
  return (
    <PortalShell portal="teacher" title="Dashboard">
      {(me) => (
        <>
          <p className="text-slate-500 font-semibold">
            Welcome back{me.email ? `, ${me.email}` : ""}. Here's your day at a glance.
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
        </>
      )}
    </PortalShell>
  );
}

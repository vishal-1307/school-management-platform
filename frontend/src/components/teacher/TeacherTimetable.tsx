import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, sectionNameOf, subjectNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { ErrorNote, Spinner } from "../portal/kit";

interface Slot {
  id: number;
  class_id: number;
  section_id: number;
  day_of_week: string;
  period_number: number;
  subject_id: number;
  is_substitute: boolean;
}

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

function TimetableView() {
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
    authFetch<Slot[]>("/api/timetable/my")
      .then(setSlots)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load timetable"));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!lookups || !slots) return <Spinner />;

  const grid = new Map(slots.map((s) => [`${s.day_of_week}-${s.period_number}`, s]));

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="px-3 py-2 text-left text-slate-400 font-bold uppercase">Period</th>
            {DAYS.map((day) => (
              <th key={day} className="px-3 py-2 text-left text-slate-400 font-bold uppercase">
                {day.slice(0, 3)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PERIODS.map((period) => (
            <tr key={period} className="border-b border-slate-50 last:border-0">
              <td className="px-3 py-2 font-extrabold text-slate-500">{period}</td>
              {DAYS.map((day) => {
                const slot = grid.get(`${day}-${period}`);
                return (
                  <td key={day} className="px-1.5 py-1.5">
                    {slot ? (
                      <div
                        className={`rounded-xl px-2 py-1.5 border ${
                          slot.is_substitute ? "bg-amber-50 border-amber-200" : "bg-indigo-50 border-indigo-100"
                        }`}
                      >
                        <p className="font-bold text-slate-800">{subjectNameOf(lookups, slot.subject_id)}</p>
                        <p className="text-slate-500 font-semibold">
                          {classNameOf(lookups, slot.class_id)} {sectionNameOf(lookups, slot.section_id)}
                        </p>
                      </div>
                    ) : (
                      <div className="min-h-[40px]" />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TeacherTimetable() {
  return (
    <PortalShell portal="teacher" title="My Timetable">
      <TimetableView />
    </PortalShell>
  );
}

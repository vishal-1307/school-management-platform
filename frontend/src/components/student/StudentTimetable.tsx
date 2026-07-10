import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, subjectNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { ErrorNote, Spinner } from "../portal/kit";
import { useStudentRecord } from "./useStudent";

interface Slot {
  id: number;
  day_of_week: string;
  period_number: number;
  subject_id: number;
  is_substitute: boolean;
}

interface Weekly {
  schedule: { day: string; slots: Slot[] }[];
}

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

/** JS getDay(): 0=Sun..6=Sat. Map onto our Mon-Sat DAYS array; Sunday falls back to Monday. */
function todayName(): string {
  const jsDay = new Date().getDay();
  return jsDay === 0 ? DAYS[0] : DAYS[jsDay - 1];
}

function TimetableView() {
  const { student, error } = useStudentRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [grid, setGrid] = useState<Map<string, Slot> | null>(null);
  const [selectedDay, setSelectedDay] = useState(todayName());

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
  }, []);

  useEffect(() => {
    if (!student) return;
    authFetch<Weekly>(
      `/api/timetable/weekly?class_id=${student.class_id}&section_id=${student.section_id}`,
    )
      .then((weekly) => {
        const map = new Map<string, Slot>();
        for (const day of weekly.schedule) {
          for (const slot of day.slots) map.set(`${day.day}-${slot.period_number}`, slot);
        }
        setGrid(map);
      })
      .catch(() => setGrid(new Map()));
  }, [student]);

  if (error) return <ErrorNote message={error} />;
  if (!student || !lookups || !grid) return <Spinner />;

  const today = todayName();
  const dayPeriods = PERIODS.map((period) => grid.get(`${selectedDay}-${period}`)).filter(
    (slot): slot is Slot => Boolean(slot),
  );

  return (
    <>
      {/* Mobile: one day at a time, empty periods hidden */}
      <div className="sm:hidden space-y-3">
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {DAYS.map((day) => (
            <button
              key={day}
              type="button"
              onClick={() => setSelectedDay(day)}
              className={`shrink-0 px-3.5 py-2.5 rounded-xl text-xs font-bold uppercase transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
                selectedDay === day ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-500"
              }`}
            >
              {day.slice(0, 3)}
              {day === today && <span className="ml-1 opacity-70">•</span>}
            </button>
          ))}
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50">
          {dayPeriods.length === 0 ? (
            <p className="px-4 py-8 text-sm text-slate-400 font-semibold text-center">
              No periods scheduled.
            </p>
          ) : (
            dayPeriods.map((slot) => (
              <div key={slot.id} className="flex items-center gap-3 px-4 py-3">
                <span className="w-8 h-8 flex-shrink-0 rounded-lg bg-indigo-50 text-indigo-700 font-extrabold text-xs flex items-center justify-center">
                  P{slot.period_number}
                </span>
                <span className="flex-1 font-bold text-slate-800 text-sm">
                  {subjectNameOf(lookups, slot.subject_id)}
                </span>
                {slot.is_substitute && (
                  <span className="text-amber-700 bg-amber-50 font-bold text-[10px] uppercase px-2 py-0.5 rounded-lg">
                    Substitute
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Desktop: full week grid */}
      <div className="hidden sm:block bg-white rounded-2xl border border-slate-100 shadow-sm overflow-x-auto">
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
                        <div className="rounded-xl px-2 py-1.5 bg-indigo-50 border border-indigo-100">
                          <p className="font-bold text-slate-800">{subjectNameOf(lookups, slot.subject_id)}</p>
                          {slot.is_substitute && (
                            <p className="text-amber-600 font-bold text-[10px]">SUBSTITUTE</p>
                          )}
                        </div>
                      ) : (
                        <div className="min-h-[36px]" />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function StudentTimetable() {
  return (
    <PortalShell portal="student" title="My Timetable">
      <TimetableView />
    </PortalShell>
  );
}

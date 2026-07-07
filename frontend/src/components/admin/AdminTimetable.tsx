import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, sectionsForClass, subjectNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { Button, Field, Modal, Select, Spinner, useToast } from "../portal/kit";

interface Slot {
  id: number;
  class_id: number;
  section_id: number;
  day_of_week: string;
  period_number: number;
  subject_id: number;
  staff_id: number;
  is_substitute: boolean;
}

interface Weekly {
  schedule: { day: string; slots: Slot[] }[];
}

interface StaffLite {
  id: number;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

function TimetablePage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [staff, setStaff] = useState<StaffLite[]>([]);
  const [classId, setClassId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const [grid, setGrid] = useState<Map<string, Slot>>(new Map());
  const [loading, setLoading] = useState(false);
  const [editCell, setEditCell] = useState<{ day: string; period: number; slot: Slot | null } | null>(null);

  const staffName = (id: number) => {
    const member = staff.find((s) => s.id === id);
    return member ? `${member.first_name} ${member.last_name.charAt(0)}.` : `#${id}`;
  };

  const load = useCallback(async () => {
    if (classId === "" || sectionId === "") return;
    setLoading(true);
    try {
      const weekly = await authFetch<Weekly>(
        `/api/timetable/weekly?class_id=${classId}&section_id=${sectionId}`,
      );
      const map = new Map<string, Slot>();
      for (const day of weekly.schedule) {
        for (const slot of day.slots) {
          map.set(`${day.day}-${slot.period_number}`, slot);
        }
      }
      setGrid(map);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load timetable", "error");
    } finally {
      setLoading(false);
    }
  }, [classId, sectionId, toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load lookups", "error"));
    authFetch<StaffLite[]>("/api/staff/").then(setStaff).catch(() => {});
  }, [toast]);
  useEffect(() => {
    load();
  }, [load]);

  if (!lookups) return <Spinner />;

  return (
    <>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Class">
          <Select
            value={classId}
            onChange={(e) => {
              setClassId(Number(e.target.value));
              setSectionId("");
            }}
            className="min-w-[140px]"
          >
            <option value="">Select…</option>
            {lookups.classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Section">
          <Select value={sectionId} onChange={(e) => setSectionId(Number(e.target.value))} className="min-w-[110px]">
            <option value="">Select…</option>
            {sectionsForClass(lookups, classId).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <p className="text-xs text-slate-400 font-semibold pb-2.5">
          Click any cell to assign a period. Double-booked teachers are rejected automatically.
        </p>
      </div>

      {loading ? (
        <Spinner />
      ) : classId !== "" && sectionId !== "" ? (
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
                        <button
                          type="button"
                          onClick={() => setEditCell({ day, period, slot: slot ?? null })}
                          className={`w-full min-h-[52px] rounded-xl px-2 py-1.5 text-left transition border ${
                            slot
                              ? slot.is_substitute
                                ? "bg-amber-50 border-amber-200 hover:border-amber-400"
                                : "bg-indigo-50 border-indigo-100 hover:border-indigo-300"
                              : "bg-slate-50 border-dashed border-slate-200 hover:border-indigo-300"
                          }`}
                        >
                          {slot ? (
                            <>
                              <p className="font-bold text-slate-800">
                                {subjectNameOf(lookups, slot.subject_id)}
                              </p>
                              <p className="text-slate-500 font-semibold">{staffName(slot.staff_id)}</p>
                              {slot.is_substitute && (
                                <p className="text-amber-600 font-bold text-[10px]">SUBSTITUTE</p>
                              )}
                            </>
                          ) : (
                            <span className="text-slate-300 font-bold">+</span>
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-slate-400 font-semibold">Pick a class and section to build its timetable.</p>
      )}

      {editCell && classId !== "" && sectionId !== "" && (
        <SlotModal
          lookups={lookups}
          staff={staff.filter((s) => s.is_active)}
          classId={classId}
          sectionId={sectionId}
          cell={editCell}
          onClose={() => setEditCell(null)}
          onDone={() => {
            setEditCell(null);
            load();
          }}
        />
      )}
    </>
  );
}

function SlotModal({
  lookups,
  staff,
  classId,
  sectionId,
  cell,
  onClose,
  onDone,
}: {
  lookups: Lookups;
  staff: StaffLite[];
  classId: number;
  sectionId: number;
  cell: { day: string; period: number; slot: Slot | null };
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [subjectId, setSubjectId] = useState<number | "">(cell.slot?.subject_id ?? "");
  const [staffId, setStaffId] = useState<number | "">(cell.slot?.staff_id ?? "");
  const [isSubstitute, setIsSubstitute] = useState(cell.slot?.is_substitute ?? false);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (subjectId === "" || staffId === "") {
      toast("Pick a subject and a teacher", "error");
      return;
    }
    setBusy(true);
    try {
      const body = {
        class_id: classId,
        section_id: sectionId,
        day_of_week: cell.day,
        period_number: cell.period,
        subject_id: subjectId,
        staff_id: staffId,
        is_substitute: isSubstitute,
      };
      if (cell.slot) {
        await authFetch(`/api/timetable/slots/${cell.slot.id}`, { method: "PUT", body });
      } else {
        await authFetch("/api/timetable/slots", { method: "POST", body });
      }
      toast("Timetable updated");
      onDone();
    } catch (error) {
      // 409 = double-booking conflict from the backend
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!cell.slot) return;
    setBusy(true);
    try {
      await authFetch(`/api/timetable/slots/${cell.slot.id}`, { method: "DELETE" });
      toast("Slot removed");
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Delete failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={`${cell.day[0].toUpperCase()}${cell.day.slice(1)} — Period ${cell.period}`}
      open
      onClose={onClose}
    >
      <div className="space-y-4">
        <Field label="Subject" required>
          <Select value={subjectId} onChange={(e) => setSubjectId(Number(e.target.value))}>
            <option value="">Select…</option>
            {lookups.subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Teacher" required>
          <Select value={staffId} onChange={(e) => setStaffId(Number(e.target.value))}>
            <option value="">Select…</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.first_name} {s.last_name}
              </option>
            ))}
          </Select>
        </Field>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-600">
          <input
            type="checkbox"
            checked={isSubstitute}
            onChange={(e) => setIsSubstitute(e.target.checked)}
          />
          Substitute teacher (temporary cover)
        </label>
        <div className="flex justify-between gap-2">
          {cell.slot ? (
            <Button variant="danger" onClick={remove} disabled={busy}>
              Remove slot
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={save} disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default function AdminTimetable() {
  return (
    <PortalShell portal="admin" title="Timetable Builder">
      <TimetablePage />
    </PortalShell>
  );
}

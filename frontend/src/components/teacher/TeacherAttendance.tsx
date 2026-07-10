import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, sectionNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { Button, ErrorNote, Field, Select, Spinner, TextInput, useToast } from "../portal/kit";
import { useTeacherRecord, classSections } from "./useTeacher";

type Status = "present" | "absent" | "late";

interface StudentLite {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  roll_number: number | null;
}

interface AttendanceRecord {
  id: number;
  student_id: number;
  status: Status;
}

const today = () => new Date().toISOString().slice(0, 10);

const STATUS_STYLES: Record<Status, string> = {
  present: "bg-emerald-600 text-white",
  absent: "bg-rose-600 text-white",
  late: "bg-amber-500 text-white",
};

function AttendanceView() {
  const toast = useToast();
  const { staff, error } = useTeacherRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [pair, setPair] = useState<string>("");
  const [date, setDate] = useState(today());
  const [students, setStudents] = useState<StudentLite[]>([]);
  const [marks, setMarks] = useState<Map<number, Status>>(new Map());
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  const pairs = classSections(staff);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
  }, []);

  useEffect(() => {
    if (!pair && pairs.length > 0) {
      setPair(`${pairs[0].class_id}-${pairs[0].section_id}`);
    }
  }, [pairs, pair]);

  const [classId, sectionId] = pair ? pair.split("-").map(Number) : [0, 0];

  const load = useCallback(async () => {
    if (!classId || !sectionId || !date) return;
    setLoading(true);
    try {
      const [list, existing] = await Promise.all([
        authFetch<{ items: StudentLite[] }>(
          `/api/students/?class_id=${classId}&section_id=${sectionId}&page_size=100`,
        ),
        authFetch<AttendanceRecord[]>(
          `/api/attendance/?class_id=${classId}&section_id=${sectionId}&date=${date}`,
        ),
      ]);
      setStudents(list.items);
      setMarks(new Map(existing.map((r) => [r.student_id, r.status])));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [classId, sectionId, date, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    const entries = students
      .filter((s) => marks.has(s.id))
      .map((s) => ({ student_id: s.id, status: marks.get(s.id)! }));
    if (entries.length === 0) {
      toast("Mark at least one student", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/attendance/mark", {
        method: "POST",
        body: { class_id: classId, section_id: sectionId, date, entries },
      });
      toast(`Attendance saved for ${entries.length} students`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

  if (error) return <ErrorNote message={error} />;
  if (!staff || !lookups) return <Spinner />;
  if (pairs.length === 0)
    return (
      <ErrorNote message="No classes are assigned to you yet — ask the school admin to add your subject assignments." />
    );

  return (
    <>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Class">
          <Select value={pair} onChange={(e) => setPair(e.target.value)} className="min-w-[170px]">
            {pairs.map((p) => (
              <option key={`${p.class_id}-${p.section_id}`} value={`${p.class_id}-${p.section_id}`}>
                {classNameOf(lookups, p.class_id)} {sectionNameOf(lookups, p.section_id)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Date">
          <TextInput type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <div className="ml-auto flex gap-2">
          <Button
            variant="secondary"
            onClick={() => setMarks(new Map(students.map((s) => [s.id, "present" as Status])))}
          >
            All Present
          </Button>
          <Button onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50">
          {students.map((student) => (
            <div key={student.id} className="flex items-center gap-4 px-4 py-2.5">
              <span className="w-10 text-xs font-bold text-slate-400">{student.roll_number ?? "—"}</span>
              <span className="flex-1 text-sm font-bold text-slate-700">
                {student.first_name} {student.last_name}
              </span>
              <div className="flex gap-1">
                {(["present", "absent", "late"] as Status[]).map((status) => (
                  <button
                    key={status}
                    type="button"
                    aria-label={status[0].toUpperCase() + status.slice(1)}
                    aria-pressed={marks.get(student.id) === status}
                    onClick={() => setMarks(new Map(marks).set(student.id, status))}
                    className={`w-11 h-11 flex items-center justify-center rounded-lg text-sm font-bold uppercase transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
                      marks.get(student.id) === status
                        ? STATUS_STYLES[status]
                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                    }`}
                  >
                    {status[0].toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {students.length === 0 && (
            <p className="px-4 py-8 text-sm text-slate-400 font-semibold">No students in this class.</p>
          )}
        </div>
      )}
    </>
  );
}

export default function TeacherAttendance() {
  return (
    <PortalShell portal="teacher" title="Mark Attendance">
      <AttendanceView />
    </PortalShell>
  );
}

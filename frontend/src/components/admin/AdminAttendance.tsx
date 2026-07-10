import { useCallback, useEffect, useState } from "react";
import { authFetch, downloadFile } from "../../lib/api";
import { getLookups, sectionsForClass, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { Button, Field, Modal, Select, Spinner, TextArea, TextInput, useToast } from "../portal/kit";

type Status = "present" | "absent" | "late";

interface AttendanceRecord {
  id: number;
  student_id: number;
  date: string;
  status: Status;
  override_reason: string | null;
}

interface StudentLite {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  roll_number: number | null;
}

interface StaffLite {
  id: number;
  first_name: string;
  last_name: string;
  designation: string | null;
  is_active: boolean;
}

interface StaffAttendanceRecord {
  id: number;
  staff_id: number;
  date: string;
  status: Status;
}

const today = () => new Date().toISOString().slice(0, 10);

const STATUS_STYLES: Record<Status, string> = {
  present: "bg-emerald-600 text-white",
  absent: "bg-rose-600 text-white",
  late: "bg-amber-500 text-white",
};

function StatusPicker({
  value,
  onChange,
}: {
  value: Status | null;
  onChange: (status: Status) => void;
}) {
  return (
    <div className="flex gap-1">
      {(["present", "absent", "late"] as Status[]).map((status) => (
        <button
          key={status}
          type="button"
          aria-label={status[0].toUpperCase() + status.slice(1)}
          aria-pressed={value === status}
          onClick={() => onChange(status)}
          className={`w-11 h-11 flex items-center justify-center rounded-lg text-sm font-bold uppercase transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
            value === status ? STATUS_STYLES[status] : "bg-slate-100 text-slate-500 hover:bg-slate-200"
          }`}
        >
          {status[0].toUpperCase()}
        </button>
      ))}
    </div>
  );
}

/* ── Student register ────────────────────────────────────────────── */

function StudentTab({ lookups }: { lookups: Lookups }) {
  const toast = useToast();
  const [classId, setClassId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const [date, setDate] = useState(today());
  const [students, setStudents] = useState<StudentLite[]>([]);
  const [records, setRecords] = useState<Map<number, AttendanceRecord>>(new Map());
  const [marks, setMarks] = useState<Map<number, Status>>(new Map());
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [override, setOverride] = useState<AttendanceRecord | null>(null);

  const load = useCallback(async () => {
    if (classId === "" || sectionId === "" || !date) return;
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
      const map = new Map(existing.map((r) => [r.student_id, r]));
      setRecords(map);
      setMarks(new Map(existing.map((r) => [r.student_id, r.status])));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [classId, sectionId, date, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const markAll = (status: Status) => {
    setMarks(new Map(students.map((s) => [s.id, status])));
  };

  const save = async () => {
    if (classId === "" || sectionId === "") return;
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
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

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
          <Select
            value={sectionId}
            onChange={(e) => setSectionId(Number(e.target.value))}
            className="min-w-[110px]"
          >
            <option value="">Select…</option>
            {sectionsForClass(lookups, classId).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
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
            onClick={() =>
              downloadFile(
                `/api/attendance/export.csv${classId !== "" ? `?class_id=${classId}` : ""}`,
                "attendance.csv",
              ).catch((error) => toast(error instanceof Error ? error.message : "Failed", "error"))
            }
          >
            Export CSV
          </Button>
          {students.length > 0 && (
            <>
              <Button variant="secondary" onClick={() => markAll("present")}>
                All Present
              </Button>
              <Button onClick={save} disabled={busy}>
                {busy ? "Saving…" : "Save Attendance"}
              </Button>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : students.length > 0 ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50">
          {students.map((student) => {
            const record = records.get(student.id);
            return (
              <div key={student.id} className="flex items-center gap-4 px-4 py-2.5">
                <span className="w-10 text-xs font-bold text-slate-400">
                  {student.roll_number ?? "—"}
                </span>
                <span className="flex-1 text-sm font-bold text-slate-700">
                  {student.first_name} {student.last_name}
                  <span className="text-slate-400 font-semibold text-xs ml-2">
                    {student.admission_number}
                  </span>
                </span>
                {record?.override_reason && (
                  <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-lg">
                    OVERRIDDEN
                  </span>
                )}
                {record && (
                  <button
                    type="button"
                    className="px-2 py-2.5 -mx-1 rounded-lg text-xs font-bold text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                    onClick={() => setOverride(record)}
                  >
                    Override
                  </button>
                )}
                <StatusPicker
                  value={marks.get(student.id) ?? null}
                  onChange={(status) => setMarks(new Map(marks).set(student.id, status))}
                />
              </div>
            );
          })}
        </div>
      ) : (
        classId !== "" &&
        sectionId !== "" && (
          <p className="text-sm text-slate-400 font-semibold">No students in this class/section.</p>
        )
      )}

      <OverrideModal record={override} onClose={() => setOverride(null)} onDone={load} />
    </>
  );
}

function OverrideModal({
  record,
  onClose,
  onDone,
}: {
  record: AttendanceRecord | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [status, setStatus] = useState<Status>("present");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (record) {
      setStatus(record.status);
      setReason("");
    }
  }, [record]);

  const run = async () => {
    if (!record) return;
    if (reason.trim().length < 5) {
      toast("A reason (min 5 characters) is required for overrides", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch(`/api/attendance/${record.id}/override`, {
        method: "PUT",
        body: { status, reason },
      });
      toast("Attendance overridden");
      onClose();
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Override failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Override Attendance (logged)" open={record !== null} onClose={onClose}>
      <div className="space-y-4">
        <Field label="New status" required>
          <Select value={status} onChange={(e) => setStatus(e.target.value as Status)}>
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="late">Late</option>
          </Select>
        </Field>
        <Field label="Reason (required, kept on record)" required>
          <TextArea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={run} disabled={busy}>
            {busy ? "Saving…" : "Override"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/* ── Staff register ──────────────────────────────────────────────── */

function StaffTab() {
  const toast = useToast();
  const [date, setDate] = useState(today());
  const [staff, setStaff] = useState<StaffLite[]>([]);
  const [marks, setMarks] = useState<Map<number, Status>>(new Map());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [members, existing] = await Promise.all([
        authFetch<StaffLite[]>("/api/staff/"),
        authFetch<StaffAttendanceRecord[]>(`/api/attendance/staff?date=${date}`),
      ]);
      setStaff(members.filter((m) => m.is_active));
      setMarks(new Map(existing.map((r) => [r.staff_id, r.status])));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [date, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    const entries = staff
      .filter((m) => marks.has(m.id))
      .map((m) => ({ staff_id: m.id, status: marks.get(m.id)! }));
    if (entries.length === 0) {
      toast("Mark at least one staff member", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/attendance/staff/mark", { method: "POST", body: { date, entries } });
      toast(`Staff attendance saved (${entries.length})`);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Date">
          <TextInput type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <div className="ml-auto flex gap-2">
          <Button
            variant="secondary"
            onClick={() => setMarks(new Map(staff.map((m) => [m.id, "present" as Status])))}
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
          {staff.map((member) => (
            <div key={member.id} className="flex items-center gap-4 px-4 py-2.5">
              <span className="flex-1 text-sm font-bold text-slate-700">
                {member.first_name} {member.last_name}
                <span className="text-slate-400 font-semibold text-xs ml-2">
                  {member.designation ?? ""}
                </span>
              </span>
              <StatusPicker
                value={marks.get(member.id) ?? null}
                onChange={(status) => setMarks(new Map(marks).set(member.id, status))}
              />
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/* ── Page ────────────────────────────────────────────────────────── */

function AttendancePage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [tab, setTab] = useState<"students" | "staff">("students");

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load lookups", "error"));
  }, [toast]);

  if (!lookups) return <Spinner />;

  return (
    <>
      <div className="flex gap-2">
        {(
          [
            ["students", "Student Attendance"],
            ["staff", "Staff Attendance"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition ${
              tab === key ? "bg-indigo-600 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "students" ? <StudentTab lookups={lookups} /> : <StaffTab />}
    </>
  );
}

export default function AdminAttendance() {
  return (
    <PortalShell portal="admin" title="Attendance Management">
      <AttendancePage />
    </PortalShell>
  );
}

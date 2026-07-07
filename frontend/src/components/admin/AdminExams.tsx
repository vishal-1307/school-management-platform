import { useCallback, useEffect, useState } from "react";
import { authFetch, downloadFile } from "../../lib/api";
import { getLookups, classNameOf, currentYearOf, subjectNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  Field,
  Modal,
  Select,
  Spinner,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";

interface ExamRow {
  id: number;
  name: string;
  exam_type: string;
  class_id: number;
  start_date: string;
  end_date: string;
  is_locked: boolean;
  results_published: boolean;
  subjects_count: number;
}

interface ExamSubject {
  id: number;
  subject_id: number;
  subject_name: string;
  max_marks: number;
  passing_marks: number;
  exam_date: string | null;
}

interface ExamDetail extends Omit<ExamRow, "subjects_count"> {
  subjects: ExamSubject[];
}

interface MarkRow {
  student_id: number;
  marks_obtained: number | null;
  grade: string | null;
}

interface StudentLite {
  id: number;
  first_name: string;
  last_name: string;
  roll_number: number | null;
}

const EXAM_TYPES = ["Unit Test", "Half-Yearly", "Annual", "Pre-Board", "Other"];

function ExamsPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [exams, setExams] = useState<ExamRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setExams(await authFetch<ExamRow[]>("/api/exams/"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load exams", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load lookups", "error"));
    load();
  }, [load, toast]);

  if (!lookups) return <Spinner />;

  const columns: Column<ExamRow>[] = [
    { header: "Exam", render: (e) => e.name },
    { header: "Type", render: (e) => e.exam_type },
    { header: "Class", render: (e) => classNameOf(lookups, e.class_id) },
    { header: "Dates", render: (e) => `${formatDate(e.start_date)} – ${formatDate(e.end_date)}` },
    { header: "Subjects", render: (e) => e.subjects_count },
    {
      header: "Status",
      render: (e) => (
        <span className="flex gap-1.5">
          {e.is_locked && (
            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-lg text-[10px] font-bold uppercase">
              Locked
            </span>
          )}
          {e.results_published ? (
            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-lg text-[10px] font-bold uppercase">
              Published
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded-lg text-[10px] font-bold uppercase">
              Hidden
            </span>
          )}
        </span>
      ),
    },
    {
      header: "Actions",
      render: (e) => (
        <button className="text-indigo-600 font-bold hover:underline" onClick={() => setDetailId(e.id)}>
          Open
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>+ Create Exam</Button>
      </div>
      <DataTable columns={columns} rows={exams} keyFor={(e) => e.id} loading={loading} />
      <CreateExamModal
        open={createOpen}
        lookups={lookups}
        onClose={() => setCreateOpen(false)}
        onDone={() => {
          setCreateOpen(false);
          load();
        }}
      />
      {detailId !== null && (
        <ExamDetailModal
          examId={detailId}
          lookups={lookups}
          onClose={() => setDetailId(null)}
          onChanged={load}
        />
      )}
    </>
  );
}

function CreateExamModal({
  open,
  lookups,
  onClose,
  onDone,
}: {
  open: boolean;
  lookups: Lookups;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [examType, setExamType] = useState(EXAM_TYPES[0]);
  const [classId, setClassId] = useState<number | "">("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [subjects, setSubjects] = useState<
    { subject_id: number | ""; max_marks: string; passing_marks: string }[]
  >([{ subject_id: "", max_marks: "100", passing_marks: "33" }]);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    const chosen = subjects.filter((s) => s.subject_id !== "");
    if (!name || classId === "" || !startDate || !endDate || chosen.length === 0) {
      toast("Name, class, dates and at least one subject are required", "error");
      return;
    }
    setBusy(true);
    try {
      const year = currentYearOf(lookups);
      await authFetch("/api/exams/", {
        method: "POST",
        body: {
          name,
          academic_year_id: year?.id ?? 1,
          class_id: classId,
          exam_type: examType,
          start_date: startDate,
          end_date: endDate,
          subjects: chosen.map((s) => ({
            subject_id: s.subject_id,
            max_marks: Number(s.max_marks),
            passing_marks: Number(s.passing_marks),
          })),
        },
      });
      toast("Exam created");
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Create failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Create Exam" open={open} onClose={onClose} wide>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Exam name" required>
          <TextInput placeholder="e.g. Unit Test I" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Type" required>
          <Select value={examType} onChange={(e) => setExamType(e.target.value)}>
            {EXAM_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
        </Field>
        <Field label="Class" required>
          <Select value={classId} onChange={(e) => setClassId(Number(e.target.value))}>
            <option value="">Select…</option>
            {lookups.classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start" required>
            <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
          <Field label="End" required>
            <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Field>
        </div>
      </div>
      <div className="space-y-2 pt-2 border-t border-slate-100">
        <p className="text-xs font-bold text-slate-600">Subjects</p>
        {subjects.map((row, i) => (
          <div key={i} className="grid grid-cols-[1fr_100px_100px_40px] gap-2 items-center">
            <Select
              value={row.subject_id}
              onChange={(e) => {
                const next = [...subjects];
                next[i] = { ...row, subject_id: Number(e.target.value) };
                setSubjects(next);
              }}
            >
              <option value="">Subject…</option>
              {lookups.subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
            <TextInput
              type="number"
              title="Max marks"
              value={row.max_marks}
              onChange={(e) => {
                const next = [...subjects];
                next[i] = { ...row, max_marks: e.target.value };
                setSubjects(next);
              }}
            />
            <TextInput
              type="number"
              title="Passing marks"
              value={row.passing_marks}
              onChange={(e) => {
                const next = [...subjects];
                next[i] = { ...row, passing_marks: e.target.value };
                setSubjects(next);
              }}
            />
            <button
              type="button"
              className="text-rose-600 font-bold"
              onClick={() => setSubjects(subjects.filter((_, j) => j !== i))}
            >
              ✕
            </button>
          </div>
        ))}
        <Button
          variant="secondary"
          onClick={() => setSubjects([...subjects, { subject_id: "", max_marks: "100", passing_marks: "33" }])}
        >
          + Add subject row
        </Button>
        <p className="text-[10px] text-slate-400 font-semibold">Columns: subject, max marks, passing marks</p>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} disabled={busy}>
          {busy ? "Creating…" : "Create Exam"}
        </Button>
      </div>
    </Modal>
  );
}

function ExamDetailModal({
  examId,
  lookups,
  onClose,
  onChanged,
}: {
  examId: number;
  lookups: Lookups;
  onClose: () => void;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [exam, setExam] = useState<ExamDetail | null>(null);
  const [marksFor, setMarksFor] = useState<ExamSubject | null>(null);

  const load = useCallback(async () => {
    try {
      setExam(await authFetch<ExamDetail>(`/api/exams/${examId}`));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load exam", "error");
    }
  }, [examId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const action = async (verb: "lock" | "unlock" | "publish") => {
    try {
      await authFetch(`/api/exams/${examId}/${verb}`, { method: "POST" });
      toast(`Exam ${verb}ed`);
      load();
      onChanged();
    } catch (error) {
      toast(error instanceof Error ? error.message : `${verb} failed`, "error");
    }
  };

  const removeExam = async () => {
    if (!confirm("Delete this exam (and all its marks)?")) return;
    try {
      await authFetch(`/api/exams/${examId}`, { method: "DELETE" });
      toast("Exam deleted");
      onClose();
      onChanged();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Delete failed", "error");
    }
  };

  return (
    <Modal title={exam ? `${exam.name} — ${classNameOf(lookups, exam.class_id)}` : "Exam"} open onClose={onClose} wide>
      {!exam ? (
        <Spinner />
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            {!exam.is_locked ? (
              <Button variant="secondary" onClick={() => action("lock")}>
                🔒 Lock marks
              </Button>
            ) : (
              <Button variant="secondary" onClick={() => action("unlock")}>
                🔓 Unlock
              </Button>
            )}
            {!exam.results_published && (
              <Button onClick={() => action("publish")}>📣 Publish results</Button>
            )}
            <Button
              variant="secondary"
              onClick={() =>
                downloadFile(`/api/exams/${examId}/marks/export.csv`, `marks-${exam.name}.csv`).catch(
                  (error) => toast(error instanceof Error ? error.message : "Failed", "error"),
                )
              }
            >
              Export Marks CSV
            </Button>
            <Button variant="danger" className="ml-auto" onClick={removeExam}>
              Delete
            </Button>
          </div>
          <div className="bg-white rounded-2xl border border-slate-100 divide-y divide-slate-50">
            {exam.subjects.map((subject) => (
              <div key={subject.id} className="flex items-center gap-4 px-4 py-2.5 text-sm font-semibold">
                <span className="flex-1">{subject.subject_name || subjectNameOf(lookups, subject.subject_id)}</span>
                <span className="text-slate-400 text-xs">
                  Max {subject.max_marks} · Pass {subject.passing_marks}
                </span>
                <button
                  className="text-indigo-600 font-bold hover:underline"
                  onClick={() => setMarksFor(subject)}
                >
                  View / Enter marks
                </button>
              </div>
            ))}
          </div>
          {marksFor && (
            <MarksGrid
              exam={exam}
              subject={marksFor}
              onClose={() => setMarksFor(null)}
            />
          )}
        </div>
      )}
    </Modal>
  );
}

export function MarksGrid({
  exam,
  subject,
  onClose,
}: {
  exam: { id: number; class_id: number; is_locked: boolean };
  subject: ExamSubject;
  onClose: () => void;
}) {
  const toast = useToast();
  const [students, setStudents] = useState<StudentLite[]>([]);
  const [marks, setMarks] = useState<Map<number, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [list, existing] = await Promise.all([
          authFetch<{ items: StudentLite[] }>(
            `/api/students/?class_id=${exam.class_id}&page_size=100`,
          ),
          authFetch<MarkRow[]>(`/api/exams/marks?exam_subject_id=${subject.id}`),
        ]);
        setStudents(list.items);
        setMarks(
          new Map(
            existing.map((m) => [m.student_id, m.marks_obtained === null ? "" : String(m.marks_obtained)]),
          ),
        );
      } catch (error) {
        toast(error instanceof Error ? error.message : "Failed to load marks", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [exam.class_id, subject.id, toast]);

  const save = async () => {
    const entries = students
      .filter((s) => (marks.get(s.id) ?? "") !== "")
      .map((s) => ({ student_id: s.id, marks_obtained: Number(marks.get(s.id)) }));
    if (entries.length === 0) {
      toast("Enter at least one mark", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/exams/marks", {
        method: "POST",
        body: { exam_subject_id: subject.id, entries },
      });
      toast(`Marks saved for ${entries.length} students`);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="border border-indigo-100 rounded-2xl p-4 space-y-3 bg-indigo-50/40">
      <div className="flex items-center justify-between">
        <p className="text-sm font-extrabold text-slate-800">
          Marks — {subject.subject_name} (max {subject.max_marks})
        </p>
        <button className="text-xs font-bold text-slate-500 hover:underline" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="bg-white rounded-xl divide-y divide-slate-50 max-h-72 overflow-y-auto">
        {students.map((student) => (
          <div key={student.id} className="flex items-center gap-3 px-3 py-2">
            <span className="w-8 text-xs font-bold text-slate-400">{student.roll_number ?? "—"}</span>
            <span className="flex-1 text-sm font-semibold text-slate-700">
              {student.first_name} {student.last_name}
            </span>
            <input
              type="number"
              min={0}
              max={subject.max_marks}
              disabled={exam.is_locked}
              value={marks.get(student.id) ?? ""}
              onChange={(e) => setMarks(new Map(marks).set(student.id, e.target.value))}
              className="w-20 px-2 py-1 border border-slate-200 rounded-lg text-sm font-bold text-right disabled:bg-slate-50"
            />
          </div>
        ))}
      </div>
      {exam.is_locked ? (
        <p className="text-xs font-bold text-slate-500">Exam is locked — unlock to edit marks.</p>
      ) : (
        <div className="flex justify-end">
          <Button onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save Marks"}
          </Button>
        </div>
      )}
    </div>
  );
}

export default function AdminExams() {
  return (
    <PortalShell portal="admin" title="Exams & Results">
      <ExamsPage />
    </PortalShell>
  );
}

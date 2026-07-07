import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { ErrorNote, Field, Select, Spinner, useToast } from "../portal/kit";
import { MarksGrid } from "../admin/AdminExams";
import { useTeacherRecord } from "./useTeacher";

interface ExamRow {
  id: number;
  name: string;
  class_id: number;
  is_locked: boolean;
  results_published: boolean;
}

interface ExamDetail extends ExamRow {
  subjects: {
    id: number;
    subject_id: number;
    subject_name: string;
    max_marks: number;
    passing_marks: number;
    exam_date: string | null;
  }[];
}

function MarksView() {
  const toast = useToast();
  const { staff, error } = useTeacherRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [exams, setExams] = useState<ExamRow[]>([]);
  const [examId, setExamId] = useState<number | "">("");
  const [exam, setExam] = useState<ExamDetail | null>(null);
  const [subjectId, setSubjectId] = useState<number | "">("");

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
    authFetch<ExamRow[]>("/api/exams/")
      .then(setExams)
      .catch((e) => toast(e instanceof Error ? e.message : "Failed to load exams", "error"));
  }, [toast]);

  useEffect(() => {
    if (examId === "") {
      setExam(null);
      return;
    }
    authFetch<ExamDetail>(`/api/exams/${examId}`)
      .then(setExam)
      .catch(() => setExam(null));
    setSubjectId("");
  }, [examId]);

  if (error) return <ErrorNote message={error} />;
  if (!staff || !lookups) return <Spinner />;

  // Exams for classes the teacher teaches; subjects limited to their own.
  const myClassIds = new Set(staff.subject_assignments.map((a) => a.class_id));
  const mySubjectIds = new Set(staff.subject_assignments.map((a) => a.subject_id));
  const myExams = exams.filter((e) => myClassIds.has(e.class_id));
  const mySubjects = exam?.subjects.filter((s) => mySubjectIds.has(s.subject_id)) ?? [];
  const selectedSubject = mySubjects.find((s) => s.id === subjectId) ?? null;

  return (
    <>
      <p className="text-sm text-slate-500 font-semibold">
        You can enter marks only for your own subjects and classes (SRS 7.5). Once the admin locks
        the exam, entries are frozen.
      </p>
      <div className="flex flex-wrap gap-3">
        <Field label="Exam">
          <Select value={examId} onChange={(e) => setExamId(Number(e.target.value))} className="min-w-[220px]">
            <option value="">Select…</option>
            {myExams.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} — {classNameOf(lookups, e.class_id)} {e.is_locked ? "(locked)" : ""}
              </option>
            ))}
          </Select>
        </Field>
        {exam && (
          <Field label="Subject">
            <Select value={subjectId} onChange={(e) => setSubjectId(Number(e.target.value))} className="min-w-[180px]">
              <option value="">Select…</option>
              {mySubjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.subject_name}
                </option>
              ))}
            </Select>
          </Field>
        )}
      </div>
      {exam && mySubjects.length === 0 && (
        <ErrorNote message="This exam has no subjects assigned to you." />
      )}
      {exam && selectedSubject && (
        <MarksGrid exam={exam} subject={selectedSubject} onClose={() => setSubjectId("")} />
      )}
    </>
  );
}

export default function TeacherMarks() {
  return (
    <PortalShell portal="teacher" title="Marks Entry">
      <MarksView />
    </PortalShell>
  );
}

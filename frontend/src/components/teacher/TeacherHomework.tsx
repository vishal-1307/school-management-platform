import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import {
  getLookups,
  classNameOf,
  sectionNameOf,
  subjectNameOf,
  type Lookups,
} from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  ErrorNote,
  Field,
  Modal,
  Select,
  Spinner,
  TextArea,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";
import { useTeacherRecord } from "./useTeacher";

interface Homework {
  id: number;
  class_id: number;
  section_id: number;
  subject_id: number;
  title: string;
  description: string | null;
  attachment_url: string | null;
  due_date: string;
  created_at: string;
}

interface Submission {
  id: number;
  homework_id: number;
  student_id: number;
  submission_url: string | null;
  submitted_at: string | null;
  status: string;
  remarks: string | null;
}

function HomeworkView() {
  const toast = useToast();
  const { staff, error } = useTeacherRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [homework, setHomework] = useState<Homework[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [submissionsFor, setSubmissionsFor] = useState<Homework | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setHomework(await authFetch<Homework[]>("/api/homework/"));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load homework", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
    load();
  }, [load]);

  if (error) return <ErrorNote message={error} />;
  if (!staff || !lookups) return <Spinner />;

  const columns: Column<Homework>[] = [
    { header: "Title", render: (h) => h.title },
    {
      header: "Class",
      render: (h) => `${classNameOf(lookups, h.class_id)} ${sectionNameOf(lookups, h.section_id)}`,
    },
    { header: "Subject", render: (h) => subjectNameOf(lookups, h.subject_id) },
    { header: "Due", className: "whitespace-nowrap", render: (h) => formatDate(h.due_date) },
    {
      header: "Actions",
      render: (h) => (
        <button className="text-indigo-600 font-bold hover:underline" onClick={() => setSubmissionsFor(h)}>
          Submissions
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>+ Post Homework</Button>
      </div>
      <DataTable columns={columns} rows={homework} keyFor={(h) => h.id} loading={loading} />
      <PostHomeworkModal
        open={createOpen}
        lookups={lookups}
        assignments={staff.subject_assignments}
        onClose={() => setCreateOpen(false)}
        onDone={() => {
          setCreateOpen(false);
          load();
        }}
      />
      {submissionsFor && (
        <SubmissionsModal homework={submissionsFor} onClose={() => setSubmissionsFor(null)} />
      )}
    </>
  );
}

function PostHomeworkModal({
  open,
  lookups,
  assignments,
  onClose,
  onDone,
}: {
  open: boolean;
  lookups: Lookups;
  assignments: { id: number; subject_id: number; class_id: number; section_id: number }[];
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [assignmentId, setAssignmentId] = useState<number | "">(assignments[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    const assignment = assignments.find((a) => a.id === assignmentId);
    if (!assignment || !title || !dueDate) {
      toast("Class/subject, title and due date are required", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/homework/", {
        method: "POST",
        body: {
          class_id: assignment.class_id,
          section_id: assignment.section_id,
          subject_id: assignment.subject_id,
          title,
          description: description || null,
          attachment_url: attachmentUrl || null,
          due_date: new Date(dueDate).toISOString(),
        },
      });
      toast("Homework posted — visible to students immediately");
      setTitle("");
      setDescription("");
      setAttachmentUrl("");
      setDueDate("");
      onDone();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Post Homework" open={open} onClose={onClose}>
      <div className="space-y-4">
        <Field label="Class / Subject" required>
          <Select value={assignmentId} onChange={(e) => setAssignmentId(Number(e.target.value))}>
            {assignments.length === 0 && <option value="">No assignments — ask admin</option>}
            {assignments.map((a) => (
              <option key={a.id} value={a.id}>
                {classNameOf(lookups, a.class_id)} {sectionNameOf(lookups, a.section_id)} —{" "}
                {subjectNameOf(lookups, a.subject_id)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Title" required>
          <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Description">
          <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label="Attachment URL (optional)">
          <TextInput
            placeholder="https://… (worksheet PDF/image)"
            value={attachmentUrl}
            onChange={(e) => setAttachmentUrl(e.target.value)}
          />
        </Field>
        <Field label="Due date" required>
          <TextInput type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={busy}>
            {busy ? "Posting…" : "Post"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function SubmissionsModal({ homework, onClose }: { homework: Homework; onClose: () => void }) {
  const toast = useToast();
  const [submissions, setSubmissions] = useState<Submission[] | null>(null);

  const load = useCallback(async () => {
    try {
      setSubmissions(await authFetch<Submission[]>(`/api/homework/${homework.id}/submissions`));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load submissions", "error");
      setSubmissions([]);
    }
  }, [homework.id, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (submission: Submission) => {
    const remarks = prompt("Remarks (optional):") ?? "";
    try {
      await authFetch(
        `/api/homework/submissions/${submission.id}/review?remarks=${encodeURIComponent(remarks)}`,
        { method: "PUT" },
      );
      toast("Marked as reviewed");
      load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    }
  };

  return (
    <Modal title={`Submissions — ${homework.title}`} open onClose={onClose} wide>
      {!submissions ? (
        <Spinner />
      ) : submissions.length === 0 ? (
        <p className="text-sm text-slate-400 font-semibold">No submissions yet.</p>
      ) : (
        <ul className="divide-y divide-slate-50">
          {submissions.map((submission) => (
            <li key={submission.id} className="flex items-center gap-3 py-2.5 text-sm font-semibold">
              <span className="flex-1">Student #{submission.student_id}</span>
              {submission.submission_url && (
                <a
                  href={submission.submission_url}
                  target="_blank"
                  rel="noopener"
                  className="text-indigo-600 font-bold hover:underline"
                >
                  Open file
                </a>
              )}
              <span
                className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase ${
                  submission.status === "reviewed"
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-amber-50 text-amber-700"
                }`}
              >
                {submission.status}
              </span>
              {submission.status !== "reviewed" && (
                <Button variant="secondary" onClick={() => review(submission)}>
                  Mark reviewed
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

export default function TeacherHomework() {
  return (
    <PortalShell portal="teacher" title="Homework & Assignments">
      <HomeworkView />
    </PortalShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, subjectNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { Button, ErrorNote, Field, Modal, Spinner, TextInput, formatDate, useToast } from "../portal/kit";
import { useStudentRecord } from "./useStudent";

interface Homework {
  id: number;
  subject_id: number;
  title: string;
  description: string | null;
  attachment_url: string | null;
  due_date: string;
}

function HomeworkView() {
  const toast = useToast();
  const { student, error } = useStudentRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [homework, setHomework] = useState<Homework[] | null>(null);
  const [submitFor, setSubmitFor] = useState<Homework | null>(null);

  const load = useCallback(async () => {
    if (!student) return;
    try {
      setHomework(
        await authFetch<Homework[]>(
          `/api/homework/?class_id=${student.class_id}&section_id=${student.section_id}`,
        ),
      );
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load homework", "error");
      setHomework([]);
    }
  }, [student, toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorNote message={error} />;
  if (!student || !lookups || !homework) return <Spinner />;

  const now = Date.now();

  return (
    <>
      <div className="space-y-3">
        {homework.length === 0 && (
          <p className="text-sm text-slate-400 font-semibold">No homework assigned yet. 🎉</p>
        )}
        {homework.map((hw) => {
          const overdue = new Date(hw.due_date).getTime() < now;
          return (
            <div key={hw.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-lg text-[10px] font-bold uppercase">
                  {subjectNameOf(lookups, hw.subject_id)}
                </span>
                <p className="font-extrabold text-slate-800">{hw.title}</p>
                <span
                  className={`ml-auto text-xs font-bold ${overdue ? "text-rose-600" : "text-slate-400"}`}
                >
                  Due {formatDate(hw.due_date)}
                </span>
              </div>
              {hw.description && (
                <p className="text-sm text-slate-600 font-semibold leading-relaxed">{hw.description}</p>
              )}
              <div className="flex gap-3 pt-1">
                {hw.attachment_url && (
                  <a
                    href={hw.attachment_url}
                    target="_blank"
                    rel="noopener"
                    className="text-indigo-600 text-sm font-bold hover:underline"
                  >
                    Download worksheet
                  </a>
                )}
                <button
                  className="text-emerald-700 text-sm font-bold hover:underline"
                  onClick={() => setSubmitFor(hw)}
                >
                  Submit work
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {submitFor && (
        <SubmitModal
          homework={submitFor}
          onClose={() => setSubmitFor(null)}
          onDone={() => setSubmitFor(null)}
        />
      )}
    </>
  );
}

function SubmitModal({
  homework,
  onClose,
  onDone,
}: {
  homework: Homework;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await authFetch("/api/homework/submit", {
        method: "POST",
        body: { homework_id: homework.id, submission_url: url || null },
      });
      toast("Homework submitted");
      onDone();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Submit failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`Submit — ${homework.title}`} open onClose={onClose}>
      <div className="space-y-4">
        <Field label="Link to your work (optional)">
          <TextInput
            placeholder="Paste a photo/Drive link, or leave empty to mark as done"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </Field>
        <p className="text-xs text-slate-400 font-semibold">
          Photo uploads directly from your phone will be enabled once the school configures file
          storage; until then paste a link (Google Drive, photo URL) or just mark it done.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy}>
            {busy ? "Submitting…" : "Submit"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function StudentHomework() {
  return (
    <PortalShell portal="student" title="Homework">
      <HomeworkView />
    </PortalShell>
  );
}

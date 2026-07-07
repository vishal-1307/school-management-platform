import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, DataTable, Field, TextArea, TextInput, formatDate, useToast, type Column } from "../portal/kit";

interface Leave {
  id: number;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  review_note: string | null;
  created_at: string;
}

const STATUS_TONES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

function LeaveView() {
  const toast = useToast();
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLeaves(await authFetch<Leave[]>("/api/leaves/mine"));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load leaves", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const apply = async () => {
    if (!startDate || !endDate || reason.trim().length < 5) {
      toast("Dates and a reason (min 5 characters) are required", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/leaves/", {
        method: "POST",
        body: { start_date: startDate, end_date: endDate, reason },
      });
      toast("Leave application submitted");
      setStartDate("");
      setEndDate("");
      setReason("");
      load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const columns: Column<Leave>[] = [
    { header: "From", render: (l) => formatDate(l.start_date) },
    { header: "To", render: (l) => formatDate(l.end_date) },
    { header: "Reason", render: (l) => l.reason, className: "max-w-[280px]" },
    {
      header: "Status",
      render: (l) => (
        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase ${STATUS_TONES[l.status]}`}>
          {l.status}
        </span>
      ),
    },
    { header: "Admin note", render: (l) => l.review_note ?? "—" },
  ];

  return (
    <>
      <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
        <h2 className="font-extrabold text-slate-800">Apply for Leave</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="From" required>
            <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
          <Field label="To" required>
            <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Field>
        </div>
        <Field label="Reason" required>
          <TextArea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="flex justify-end">
          <Button onClick={apply} disabled={busy}>
            {busy ? "Submitting…" : "Submit Application"}
          </Button>
        </div>
      </section>
      <DataTable
        columns={columns}
        rows={leaves}
        keyFor={(l) => l.id}
        loading={loading}
        empty="No leave applications yet."
      />
    </>
  );
}

export default function TeacherLeave() {
  return (
    <PortalShell portal="teacher" title="Leave Application">
      <LeaveView />
    </PortalShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, DataTable, formatDate, useToast, type Column } from "../portal/kit";

interface Leave {
  id: number;
  staff_id: number;
  staff_name?: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  reviewed_by_id: number | null;
  created_at: string;
}

const STATUS_TONES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

function LeavesPage() {
  const toast = useToast();
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLeaves(await authFetch<Leave[]>("/api/leaves/"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load leave requests", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (leave: Leave, decision: "approved" | "rejected") => {
    try {
      await authFetch(`/api/leaves/${leave.id}/review`, {
        method: "PUT",
        body: { status: decision },
      });
      toast(`Leave ${decision}`);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const columns: Column<Leave>[] = [
    { header: "Staff", render: (l) => l.staff_name ?? `#${l.staff_id}` },
    { header: "From", render: (l) => formatDate(l.start_date) },
    { header: "To", render: (l) => formatDate(l.end_date) },
    { header: "Reason", render: (l) => l.reason, className: "max-w-[280px]" },
    {
      header: "Status",
      render: (l) => (
        <span
          className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase ${STATUS_TONES[l.status] ?? "bg-slate-100"}`}
        >
          {l.status}
        </span>
      ),
    },
    {
      header: "Actions",
      render: (l) =>
        l.status === "pending" ? (
          <span className="flex gap-2">
            <Button onClick={() => review(l, "approved")}>Approve</Button>
            <Button variant="danger" onClick={() => review(l, "rejected")}>
              Reject
            </Button>
          </span>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={leaves}
      keyFor={(l) => l.id}
      loading={loading}
      empty="No leave applications yet."
    />
  );
}

export default function AdminLeaves() {
  return (
    <PortalShell portal="admin" title="Staff Leave Requests">
      <LeavesPage />
    </PortalShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { DataTable, Select, TextInput, useDebounced, useToast, type Column } from "../portal/kit";

interface MessageLog {
  id: number;
  recipient_phone: string;
  message_type: string;
  content_summary: string | null;
  template_name: string | null;
  delivery_status: string;
  sent_at: string;
}

const STATUS_TONES: Record<string, string> = {
  sent: "bg-sky-50 text-sky-700",
  delivered: "bg-emerald-50 text-emerald-700",
  failed: "bg-rose-50 text-rose-700",
  queued: "bg-slate-100 text-slate-600",
  skipped: "bg-amber-50 text-amber-700",
};

function CommunicationPage() {
  const toast = useToast();
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState("");
  const debouncedPhone = useDebounced(phone);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page_size: "100" });
      if (debouncedPhone) params.set("phone", debouncedPhone);
      if (status) params.set("delivery_status", status);
      setMessages(await authFetch<MessageLog[]>(`/api/communication/?${params}`));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load log", "error");
    } finally {
      setLoading(false);
    }
  }, [debouncedPhone, status, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns: Column<MessageLog>[] = [
    { header: "To", render: (m) => m.recipient_phone },
    { header: "Type", render: (m) => m.template_name ?? m.message_type },
    { header: "Content", render: (m) => m.content_summary ?? "—", className: "max-w-[320px] truncate" },
    {
      header: "Status",
      render: (m) => (
        <span
          className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase ${STATUS_TONES[m.delivery_status] ?? "bg-slate-100 text-slate-600"}`}
        >
          {m.delivery_status}
        </span>
      ),
    },
    { header: "Sent", render: (m) => new Date(m.sent_at).toLocaleString("en-IN") },
  ];

  return (
    <>
      <p className="text-sm text-slate-500 font-semibold">
        Every WhatsApp message the platform sends is logged here (SRS 6.13). "Skipped" means the
        automation ran but WhatsApp credentials aren't configured yet.
      </p>
      <div className="flex gap-3">
        <TextInput
          placeholder="Filter by phone…"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="max-w-xs"
        />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-[160px]">
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="sent">Sent</option>
          <option value="delivered">Delivered</option>
          <option value="failed">Failed</option>
          <option value="skipped">Skipped</option>
        </Select>
      </div>
      <DataTable
        columns={columns}
        rows={messages}
        keyFor={(m) => m.id}
        loading={loading}
        empty="No messages sent yet."
      />
    </>
  );
}

export default function AdminCommunication() {
  return (
    <PortalShell portal="admin" title="Communication Log">
      <CommunicationPage />
    </PortalShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
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

interface Notice {
  id: number;
  title: string;
  content: string;
  attachment_url: string | null;
  audience: string;
  target_class_id: number | null;
  channels: string[] | null;
  scheduled_at: string | null;
  published_at: string | null;
  created_at: string;
}

const CHANNELS = [
  { key: "website", label: "Public Website" },
  { key: "app", label: "Student/Teacher Portal" },
  { key: "whatsapp", label: "WhatsApp Broadcast" },
];

function NoticesPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [composeOpen, setComposeOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setNotices(await authFetch<Notice[]>("/api/notices/?published_only=false&page_size=100"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load notices", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
    load();
  }, [load]);

  const remove = async (notice: Notice) => {
    if (!confirm(`Delete notice "${notice.title}"?`)) return;
    try {
      await authFetch(`/api/notices/${notice.id}`, { method: "DELETE" });
      toast("Notice deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Delete failed", "error");
    }
  };

  const broadcast = async (notice: Notice) => {
    if (!confirm(`Send "${notice.title}" to all parents on WhatsApp now?`)) return;
    try {
      const result = await authFetch<{ message: string }>(`/api/notices/${notice.id}/broadcast`, {
        method: "POST",
      });
      toast(result.message);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Broadcast failed", "error");
    }
  };

  const columns: Column<Notice>[] = [
    { header: "Title", render: (n) => n.title },
    {
      header: "Audience",
      render: (n) =>
        n.audience === "class" && lookups
          ? `Class: ${classNameOf(lookups, n.target_class_id)}`
          : n.audience,
    },
    {
      header: "Channels",
      render: (n) => (n.channels ?? []).join(", ") || "—",
    },
    {
      header: "Status",
      render: (n) =>
        n.published_at ? (
          <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-lg text-[10px] font-bold uppercase">
            Published
          </span>
        ) : (
          <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded-lg text-[10px] font-bold uppercase">
            Scheduled {formatDate(n.scheduled_at)}
          </span>
        ),
    },
    { header: "Created", className: "whitespace-nowrap", render: (n) => formatDate(n.created_at) },
    {
      header: "Actions",
      render: (n) => (
        <span className="flex gap-2">
          {(n.channels ?? []).includes("whatsapp") && (
            <button className="text-emerald-600 font-bold hover:underline" onClick={() => broadcast(n)}>
              Send WA
            </button>
          )}
          <button className="text-rose-600 font-bold hover:underline" onClick={() => remove(n)}>
            Delete
          </button>
        </span>
      ),
    },
  ];

  if (!lookups) return <Spinner />;

  return (
    <>
      <div className="flex justify-end">
        <Button onClick={() => setComposeOpen(true)}>+ Compose Notice</Button>
      </div>
      <DataTable columns={columns} rows={notices} keyFor={(n) => n.id} loading={loading} />
      <ComposeModal
        open={composeOpen}
        lookups={lookups}
        onClose={() => setComposeOpen(false)}
        onDone={() => {
          setComposeOpen(false);
          load();
        }}
      />
    </>
  );
}

function ComposeModal({
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
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [audience, setAudience] = useState("everyone");
  const [targetClassId, setTargetClassId] = useState<number | "">("");
  const [channels, setChannels] = useState<string[]>(["website", "app"]);
  const [attachmentUrl, setAttachmentUrl] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [busy, setBusy] = useState(false);

  const toggleChannel = (key: string) => {
    setChannels((prev) => (prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]));
  };

  const save = async () => {
    if (!title || !content) {
      toast("Title and content are required", "error");
      return;
    }
    if (audience === "class" && targetClassId === "") {
      toast("Pick the target class", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch("/api/notices/", {
        method: "POST",
        body: {
          title,
          content,
          attachment_url: attachmentUrl || null,
          audience,
          target_class_id: audience === "class" ? targetClassId : null,
          channels,
          scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
        },
      });
      toast(scheduledAt ? "Notice scheduled" : "Notice published");
      setTitle("");
      setContent("");
      setScheduledAt("");
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Compose Notice" open={open} onClose={onClose} wide>
      <div className="space-y-4">
        <Field label="Title" required>
          <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Content" required>
          <TextArea rows={4} value={content} onChange={(e) => setContent(e.target.value)} />
        </Field>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Audience" required>
            <Select value={audience} onChange={(e) => setAudience(e.target.value)}>
              <option value="everyone">Everyone</option>
              <option value="class">Specific class</option>
              <option value="staff">Staff only</option>
            </Select>
          </Field>
          {audience === "class" && (
            <Field label="Target class" required>
              <Select value={targetClassId} onChange={(e) => setTargetClassId(Number(e.target.value))}>
                <option value="">Select…</option>
                {lookups.classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Field label="Attachment URL (optional)">
            <TextInput
              placeholder="https://… (PDF circular)"
              value={attachmentUrl}
              onChange={(e) => setAttachmentUrl(e.target.value)}
            />
          </Field>
          <Field label="Schedule for later (optional)">
            <TextInput
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
            />
          </Field>
        </div>
        <Field label="Channels">
          <div className="flex flex-wrap gap-3">
            {CHANNELS.map((channel) => (
              <label
                key={channel.key}
                className="flex items-center gap-2 text-sm font-bold text-slate-600 px-2 py-2 -mx-2 rounded-xl hover:bg-slate-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  className="w-5 h-5 accent-indigo-600"
                  checked={channels.includes(channel.key)}
                  onChange={() => toggleChannel(channel.key)}
                />
                {channel.label}
              </label>
            ))}
          </div>
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={busy}>
            {busy ? "Publishing…" : scheduledAt ? "Schedule" : "Publish"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function AdminNotices() {
  return (
    <PortalShell portal="admin" title="Notices & Circulars">
      <NoticesPage />
    </PortalShell>
  );
}

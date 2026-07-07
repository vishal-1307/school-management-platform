import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, formatDate, useToast } from "../portal/kit";

interface ContactMessage {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  message: string;
  is_read: boolean;
  created_at: string;
}

function MessagesPage() {
  const toast = useToast();
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = useCallback(async () => {
    try {
      setMessages(
        await authFetch<ContactMessage[]>(
          `/api/contact-messages/?unread_only=${unreadOnly}&page_size=100`,
        ),
      );
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load messages", "error");
    }
  }, [unreadOnly, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (message: ContactMessage) => {
    try {
      await authFetch(`/api/contact-messages/${message.id}/read`, { method: "PUT" });
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const remove = async (message: ContactMessage) => {
    if (!confirm("Delete this message?")) return;
    try {
      await authFetch(`/api/contact-messages/${message.id}`, { method: "DELETE" });
      toast("Deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  return (
    <>
      <label className="flex items-center gap-2 text-sm font-bold text-slate-600">
        <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
        Unread only
      </label>
      <div className="space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400 font-semibold">No messages.</p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`bg-white rounded-2xl border p-5 space-y-2 ${
              message.is_read ? "border-slate-100" : "border-indigo-200 shadow-sm"
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-extrabold text-slate-800">{message.name}</p>
              {!message.is_read && (
                <span className="px-2 py-0.5 bg-indigo-600 text-white rounded-lg text-[10px] font-bold uppercase">
                  New
                </span>
              )}
              <span className="ml-auto text-xs text-slate-400 font-bold">
                {formatDate(message.created_at)}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-semibold">
              {[message.phone, message.email].filter(Boolean).join(" · ") || "No contact info"}
            </p>
            <p className="text-sm text-slate-700 font-semibold leading-relaxed">{message.message}</p>
            <div className="flex gap-2 pt-1">
              {!message.is_read && (
                <Button variant="secondary" onClick={() => markRead(message)}>
                  Mark read
                </Button>
              )}
              {message.phone && (
                <a
                  href={`https://wa.me/91${message.phone.replace(/\D/g, "").slice(-10)}`}
                  target="_blank"
                  rel="noopener"
                  className="px-4 py-2.5 rounded-xl text-sm font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition"
                >
                  Reply on WhatsApp
                </a>
              )}
              <Button variant="danger" className="ml-auto" onClick={() => remove(message)}>
                Delete
              </Button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default function AdminMessages() {
  return (
    <PortalShell portal="admin" title="Website Enquiries Inbox">
      <MessagesPage />
    </PortalShell>
  );
}

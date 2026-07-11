/**
 * Role-scoped AI assistant chat panel — floating action button + right-docked
 * drawer, mounted once in PortalShell for every portal page. The wire
 * contract with the backend is plain-text transcript turns only; a WRITE
 * action never runs from a single message — it comes back as a
 * `pending_action` that must be explicitly confirmed or cancelled here.
 */

import { useEffect, useRef, useState } from "react";
import { Check, Send, Sparkles, X } from "lucide-react";
import { authFetch } from "../../lib/api";
import type { Me } from "../../lib/authStore";
import { Button, TextArea, useToast } from "./kit";

interface Turn {
  role: "user" | "assistant";
  text: string;
}

interface PendingActionPayload {
  action_id: string;
  title: string;
  summary: string;
  preview: unknown;
}

interface ChatResponse {
  reply: string;
  pending_action?: PendingActionPayload | null;
}

const PLACEHOLDER_BY_PORTAL: Record<string, string> = {
  admin: "Ask about a student, staff member, fees, or an enquiry…",
  teacher: "Ask about your classes, or say who was absent today…",
  student: "Ask about your attendance, homework, fees, or timetable…",
};

function PreviewDetail({ preview }: { preview: unknown }) {
  if (!preview || typeof preview !== "object") return null;
  const data = preview as Record<string, unknown>;

  if (Array.isArray(data.roster)) {
    const roster = data.roster as Array<{ student_id: number; name: string; status: string }>;
    return (
      <div className="max-h-40 overflow-y-auto rounded-xl border border-slate-100 divide-y divide-slate-50">
        {roster.map((row) => (
          <div key={row.student_id} className="flex items-center justify-between px-3 py-1.5 text-xs">
            <span className="font-semibold text-slate-700">{row.name}</span>
            <span
              className={`px-2 py-0.5 rounded-lg font-bold uppercase text-[10px] ${
                row.status === "absent" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"
              }`}
            >
              {row.status}
            </span>
          </div>
        ))}
      </div>
    );
  }

  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-100 divide-y divide-slate-50 text-xs">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center justify-between px-3 py-1.5">
          <span className="text-slate-400 font-bold uppercase tracking-wide">{key.replace(/_/g, " ")}</span>
          <span className="font-semibold text-slate-700">{String(value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function ChatPanel({
  portal,
  me,
  hideFab = false,
}: {
  portal: "admin" | "teacher" | "student";
  me: Me;
  hideFab?: boolean;
}) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingActionPayload | null>(null);
  const [confirming, setConfirming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript, busy, pendingAction]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const nextTranscript: Turn[] = [...transcript, { role: "user", text }];
    setTranscript(nextTranscript);
    setInput("");
    setBusy(true);
    try {
      const result = await authFetch<ChatResponse>("/api/ai/assistant/chat", {
        method: "POST",
        body: { transcript: nextTranscript },
      });
      setTranscript((prev) => [...prev, { role: "assistant", text: result.reply }]);
      setPendingAction(result.pending_action ?? null);
    } catch (error) {
      toast(error instanceof Error ? error.message : "The assistant didn't respond", "error");
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!pendingAction) return;
    setConfirming(true);
    try {
      const result = await authFetch<{ reply: string }>("/api/ai/assistant/confirm", {
        method: "POST",
        body: { action_id: pendingAction.action_id },
      });
      setTranscript((prev) => [...prev, { role: "assistant", text: result.reply }]);
      setPendingAction(null);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Couldn't complete that action", "error");
    } finally {
      setConfirming(false);
    }
  };

  const cancel = async () => {
    if (!pendingAction) return;
    const actionId = pendingAction.action_id;
    setPendingAction(null);
    try {
      await authFetch("/api/ai/assistant/cancel", { method: "POST", body: { action_id: actionId } });
    } catch {
      /* best-effort — the action expires on its own either way */
    }
    setTranscript((prev) => [...prev, { role: "assistant", text: "Cancelled — no changes were made." }]);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open assistant"
        className={`fixed bottom-4 right-4 z-40 w-14 h-14 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center justify-center transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
          hideFab ? "hidden" : ""
        }`}
      >
        <Sparkles className="w-6 h-6" />
      </button>
    );
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-slate-900/60" onClick={() => setOpen(false)} />
      <div className="fixed top-0 right-0 z-50 h-full w-96 max-w-[90vw] bg-white shadow-2xl flex flex-col">
        <div className="p-4 border-b border-slate-100 flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <p className="font-extrabold text-slate-900 text-sm leading-tight">Assistant</p>
            <p className="text-[11px] text-slate-400 font-semibold truncate">{me.display_name || me.login_id}</p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close assistant"
            className="ml-auto p-3 -m-1.5 rounded-xl hover:bg-slate-100 text-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {transcript.length === 0 && (
            <p className="text-sm text-slate-400 font-semibold text-center py-8">
              {PLACEHOLDER_BY_PORTAL[portal]}
            </p>
          )}
          {transcript.map((turn, i) => (
            <div key={i} className={`flex ${turn.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm font-semibold whitespace-pre-wrap ${
                  turn.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-700"
                }`}
              >
                {turn.text}
              </div>
            </div>
          ))}

          {busy && (
            <div className="flex justify-start">
              <div className="bg-slate-100 text-slate-400 px-4 py-2.5 rounded-2xl text-sm font-bold">
                Thinking…
              </div>
            </div>
          )}

          {pendingAction && (
            <div className="bg-white border-2 border-indigo-200 rounded-2xl p-4 space-y-3">
              <p className="font-extrabold text-slate-900 text-sm">{pendingAction.title}</p>
              <p className="text-sm text-slate-600 font-semibold">{pendingAction.summary}</p>
              <PreviewDetail preview={pendingAction.preview} />
              <div className="flex gap-2 pt-1">
                <Button onClick={confirm} disabled={confirming} className="flex-1">
                  <span className="inline-flex items-center gap-1.5 justify-center">
                    <Check className="w-4 h-4" /> {confirming ? "Confirming…" : "Confirm"}
                  </span>
                </Button>
                <Button variant="secondary" onClick={cancel} disabled={confirming} className="flex-1">
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-slate-100 flex items-end gap-2">
          <TextArea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Type a message…"
            disabled={busy}
            className="flex-1"
          />
          <Button onClick={send} disabled={busy || !input.trim()} aria-label="Send">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </>
  );
}

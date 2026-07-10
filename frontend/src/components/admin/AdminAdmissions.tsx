import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, Field, Modal, Select, Spinner, TextArea, formatDate, useToast } from "../portal/kit";

interface Enquiry {
  id: number;
  child_name: string;
  dob: string | null;
  class_applying: string;
  parent_name: string;
  phone: string;
  email: string | null;
  address: string | null;
  source: string | null;
  message: string | null;
  status: string;
  notes: string | null;
  created_at: string;
}

const PIPELINE = [
  { status: "new", label: "New", tone: "bg-indigo-50 border-indigo-100" },
  { status: "contacted", label: "Contacted", tone: "bg-amber-50 border-amber-100" },
  { status: "visited", label: "Visited", tone: "bg-sky-50 border-sky-100" },
  { status: "admitted", label: "Admitted", tone: "bg-emerald-50 border-emerald-100" },
  { status: "not_interested", label: "Not Interested", tone: "bg-slate-50 border-slate-100" },
];

interface EnquiryList {
  items: Enquiry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function AdmissionsPage() {
  const toast = useToast();
  const [enquiries, setEnquiries] = useState<Enquiry[] | null>(null);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Enquiry | null>(null);
  const [status, setStatus] = useState("new");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      // Backend caps page_size at 100; fetch first 100 (newest first).
      const list = await authFetch<EnquiryList>("/api/admissions/?page_size=100");
      setEnquiries(list.items);
      setTotal(list.total);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load enquiries", "error");
      setEnquiries([]);
      setTotal(0);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const open = (enquiry: Enquiry) => {
    setSelected(enquiry);
    setStatus(enquiry.status);
    setNotes(enquiry.notes ?? "");
  };

  const save = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await authFetch(`/api/admissions/${selected.id}`, {
        method: "PUT",
        body: { status, notes: notes || null },
      });
      toast("Enquiry updated");
      setSelected(null);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Update failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const convertToStudent = () => {
    if (!selected) return;
    // Pre-fill the Add Student form on the students page.
    localStorage.setItem(
      "student_prefill",
      JSON.stringify({
        first_name: selected.child_name.split(" ")[0] ?? "",
        last_name: selected.child_name.split(" ").slice(1).join(" "),
        dob: selected.dob ?? "",
        address: selected.address ?? "",
        parent_name: selected.parent_name,
        parent_phone: selected.phone,
      }),
    );
    window.location.href = "/admin/students?new=1";
  };

  const remove = async () => {
    if (!selected) return;
    if (!confirm("Delete this enquiry permanently?")) return;
    try {
      await authFetch(`/api/admissions/${selected.id}`, { method: "DELETE" });
      toast("Enquiry deleted");
      setSelected(null);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Delete failed", "error");
    }
  };

  if (enquiries === null) return <Spinner />;

  return (
    <>
      {total > enquiries.length && (
        <p className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-4 py-2.5">
          Showing the {enquiries.length} most recent of {total} enquiries. Filter or resolve older
          ones to see more.
        </p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-4 items-start">
        {PIPELINE.map((column) => {
          const cards = enquiries.filter((e) => e.status === column.status);
          return (
            <div key={column.status} className={`rounded-2xl border p-3 space-y-3 ${column.tone}`}>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 px-1">
                {column.label} ({cards.length})
              </p>
              {cards.map((enquiry) => (
                <button
                  key={enquiry.id}
                  type="button"
                  onClick={() => open(enquiry)}
                  className="w-full bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition p-3 text-left space-y-1"
                >
                  <p className="font-extrabold text-slate-800 text-sm">{enquiry.child_name}</p>
                  <p className="text-xs text-slate-500 font-semibold">
                    {enquiry.class_applying} · {enquiry.parent_name}
                  </p>
                  <p className="text-xs text-slate-400 font-semibold">
                    {enquiry.phone} · {formatDate(enquiry.created_at)}
                  </p>
                </button>
              ))}
              {cards.length === 0 && (
                <p className="text-xs text-slate-400 font-semibold px-1 pb-1">Empty</p>
              )}
            </div>
          );
        })}
      </div>

      <Modal
        title={selected ? `Enquiry — ${selected.child_name}` : ""}
        open={selected !== null}
        onClose={() => setSelected(null)}
      >
        {selected && (
          <div className="space-y-4">
            <div className="text-sm font-semibold text-slate-600 space-y-1 bg-slate-50 rounded-xl p-4">
              <p>Class applying: <b>{selected.class_applying}</b></p>
              <p>Parent: <b>{selected.parent_name}</b> · {selected.phone}</p>
              {selected.email && <p>Email: {selected.email}</p>}
              {selected.dob && <p>DOB: {formatDate(selected.dob)}</p>}
              {selected.address && <p>Address: {selected.address}</p>}
              {selected.source && <p>Heard via: {selected.source}</p>}
              {selected.message && <p className="italic">“{selected.message}”</p>}
            </div>
            <Field label="Status">
              <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                {PIPELINE.map((p) => (
                  <option key={p.status} value={p.status}>
                    {p.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Follow-up notes">
              <TextArea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>
            <div className="flex flex-wrap justify-between gap-2">
              <div className="flex gap-2">
                <Button variant="danger" onClick={remove}>
                  Delete
                </Button>
                {status === "admitted" && (
                  <Button variant="secondary" onClick={convertToStudent}>
                    Convert to Student →
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setSelected(null)}>
                  Cancel
                </Button>
                <Button onClick={save} disabled={busy}>
                  {busy ? "Saving…" : "Save"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}

export default function AdminAdmissions() {
  return (
    <PortalShell portal="admin" title="Admissions / Enquiry Pipeline">
      <AdmissionsPage />
    </PortalShell>
  );
}

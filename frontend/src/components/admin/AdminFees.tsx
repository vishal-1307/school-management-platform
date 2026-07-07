import { useCallback, useEffect, useState } from "react";
import { authFetch, downloadFile, openHtmlDocument } from "../../lib/api";
import {
  getLookups,
  classNameOf,
  currentYearOf,
  type Lookups,
} from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  Field,
  Modal,
  Select,
  Spinner,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";

interface FeeStructure {
  id: number;
  class_id: number;
  academic_year_id: number;
  fee_head: string;
  amount: number;
  due_date: string;
  term: string | null;
}

interface Transaction {
  id: number;
  student_id: number;
  fee_structure_id: number;
  amount_paid: number;
  payment_mode: string;
  receipt_number: string;
  paid_at: string;
}

interface Defaulter {
  student_id: number;
  admission_number: string;
  student_name: string;
  class_name: string;
  fee_head: string;
  amount_due: number;
  amount_paid: number;
  balance: number;
  due_date: string;
}

interface StudentLite {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  class_id: number;
}

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;

type Tab = "structures" | "payments" | "defaulters";

function FeesPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [tab, setTab] = useState<Tab>("structures");

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load lookups", "error"));
  }, [toast]);

  if (!lookups) return <Spinner />;

  return (
    <>
      <div className="flex gap-2">
        {(
          [
            ["structures", "Fee Structures"],
            ["payments", "Payments & Receipts"],
            ["defaulters", "Defaulters"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition ${
              tab === key ? "bg-indigo-600 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "structures" && <StructuresTab lookups={lookups} />}
      {tab === "payments" && <PaymentsTab lookups={lookups} />}
      {tab === "defaulters" && <DefaultersTab lookups={lookups} />}
    </>
  );
}

/* ── Structures ──────────────────────────────────────────────────── */

function StructuresTab({ lookups }: { lookups: Lookups }) {
  const toast = useToast();
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<FeeStructure | "new" | null>(null);
  const [form, setForm] = useState({ class_id: "" as number | "", fee_head: "", amount: "", due_date: "", term: "" });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStructures(await authFetch<FeeStructure[]>("/api/fees/structures"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    const year = currentYearOf(lookups);
    if (form.class_id === "" || !form.fee_head || !form.amount || !form.due_date || !year) {
      toast("Class, fee head, amount and due date are required", "error");
      return;
    }
    setSaving(true);
    try {
      const body = {
        class_id: form.class_id,
        academic_year_id: year.id,
        fee_head: form.fee_head,
        amount: Number(form.amount),
        due_date: form.due_date,
        term: form.term || null,
      };
      if (editing === "new") {
        await authFetch("/api/fees/structures", { method: "POST", body });
        toast("Fee structure created");
      } else if (editing) {
        await authFetch(`/api/fees/structures/${editing.id}`, { method: "PUT", body });
        toast("Fee structure updated");
      }
      setEditing(null);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (structure: FeeStructure) => {
    if (!confirm(`Delete "${structure.fee_head}" for ${classNameOf(lookups, structure.class_id)}?`)) return;
    try {
      await authFetch(`/api/fees/structures/${structure.id}`, { method: "DELETE" });
      toast("Deleted");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Delete failed", "error");
    }
  };

  const columns: Column<FeeStructure>[] = [
    { header: "Class", render: (s) => classNameOf(lookups, s.class_id) },
    { header: "Fee Head", render: (s) => s.fee_head },
    { header: "Term", render: (s) => s.term ?? "—" },
    { header: "Amount", render: (s) => rupees(s.amount) },
    { header: "Due Date", render: (s) => formatDate(s.due_date) },
    {
      header: "Actions",
      render: (s) => (
        <span className="flex gap-2">
          <button
            className="text-indigo-600 font-bold hover:underline"
            onClick={() => {
              setForm({
                class_id: s.class_id,
                fee_head: s.fee_head,
                amount: String(s.amount),
                due_date: s.due_date,
                term: s.term ?? "",
              });
              setEditing(s);
            }}
          >
            Edit
          </button>
          <button className="text-rose-600 font-bold hover:underline" onClick={() => remove(s)}>
            Delete
          </button>
        </span>
      ),
    },
  ];

  return (
    <>
      <div className="flex justify-end">
        <Button
          onClick={() => {
            setForm({ class_id: "", fee_head: "", amount: "", due_date: "", term: "" });
            setEditing("new");
          }}
        >
          + Add Fee Structure
        </Button>
      </div>
      <DataTable columns={columns} rows={structures} keyFor={(s) => s.id} loading={loading} />

      <Modal
        title={editing === "new" ? "Add Fee Structure" : "Edit Fee Structure"}
        open={editing !== null}
        onClose={() => setEditing(null)}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Class" required>
            <Select value={form.class_id} onChange={(e) => setForm({ ...form, class_id: Number(e.target.value) })}>
              <option value="">Select…</option>
              {lookups.classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Fee head" required>
            <TextInput
              placeholder="e.g. Tuition Fee"
              value={form.fee_head}
              onChange={(e) => setForm({ ...form, fee_head: e.target.value })}
            />
          </Field>
          <Field label="Amount (₹)" required>
            <TextInput type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </Field>
          <Field label="Due date" required>
            <TextInput type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          </Field>
          <Field label="Term">
            <TextInput
              placeholder="e.g. Term 1"
              value={form.term}
              onChange={(e) => setForm({ ...form, term: e.target.value })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={() => setEditing(null)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </Modal>
    </>
  );
}

/* ── Payments ────────────────────────────────────────────────────── */

function PaymentsTab({ lookups }: { lookups: Lookups }) {
  const toast = useToast();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [students, setStudents] = useState<Map<number, StudentLite>>(new Map());
  const [loading, setLoading] = useState(true);
  const [payOpen, setPayOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const txns = await authFetch<Transaction[]>("/api/fees/transactions");
      setTransactions(txns);
      const list = await authFetch<{ items: StudentLite[] }>("/api/students/?page_size=100");
      setStudents(new Map(list.items.map((s) => [s.id, s])));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns: Column<Transaction>[] = [
    { header: "Receipt", render: (t) => t.receipt_number },
    {
      header: "Student",
      render: (t) => {
        const s = students.get(t.student_id);
        return s ? `${s.first_name} ${s.last_name} (${s.admission_number})` : `#${t.student_id}`;
      },
    },
    { header: "Amount", render: (t) => rupees(t.amount_paid) },
    { header: "Mode", render: (t) => t.payment_mode.toUpperCase() },
    { header: "Date", render: (t) => formatDate(t.paid_at) },
    {
      header: "Receipt",
      render: (t) => (
        <button
          className="text-indigo-600 font-bold hover:underline"
          onClick={() =>
            openHtmlDocument(`/api/fees/receipts/${t.id}/html`).catch((error) =>
              toast(error instanceof Error ? error.message : "Failed", "error"),
            )
          }
        >
          Print
        </button>
      ),
    },
  ];

  return (
    <>
      <div className="flex justify-end gap-2">
        <Button
          variant="secondary"
          onClick={() =>
            downloadFile("/api/fees/transactions/export.csv", "fee-transactions.csv").catch(
              (error) => toast(error instanceof Error ? error.message : "Failed", "error"),
            )
          }
        >
          Export CSV
        </Button>
        <Button onClick={() => setPayOpen(true)}>+ Record Payment</Button>
      </div>
      <DataTable columns={columns} rows={transactions} keyFor={(t) => t.id} loading={loading} />
      <RecordPaymentModal
        open={payOpen}
        lookups={lookups}
        onClose={() => setPayOpen(false)}
        onDone={() => {
          setPayOpen(false);
          load();
        }}
      />
    </>
  );
}

function RecordPaymentModal({
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
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<StudentLite[]>([]);
  const [student, setStudent] = useState<StudentLite | null>(null);
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [structureId, setStructureId] = useState<number | "">("");
  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState("cash");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (search.length < 2) {
      setOptions([]);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const list = await authFetch<{ items: StudentLite[] }>(
          `/api/students/?search=${encodeURIComponent(search)}&page_size=10`,
        );
        setOptions(list.items);
      } catch {
        /* ignore */
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [search]);

  useEffect(() => {
    if (!student) return;
    authFetch<FeeStructure[]>(`/api/fees/structures?class_id=${student.class_id}`)
      .then(setStructures)
      .catch(() => setStructures([]));
  }, [student]);

  useEffect(() => {
    const structure = structures.find((s) => s.id === structureId);
    if (structure) setAmount(String(structure.amount));
  }, [structureId, structures]);

  const pay = async () => {
    if (!student || structureId === "" || !amount) {
      toast("Pick a student, fee head and amount", "error");
      return;
    }
    setBusy(true);
    try {
      const receipt = await authFetch<Transaction>("/api/fees/pay", {
        method: "POST",
        body: {
          student_id: student.id,
          fee_structure_id: structureId,
          amount_paid: Number(amount),
          payment_mode: mode,
        },
      });
      toast(`Payment recorded — receipt ${receipt.receipt_number}`);
      openHtmlDocument(`/api/fees/receipts/${receipt.id}/html`).catch(() => {});
      setStudent(null);
      setSearch("");
      setStructureId("");
      setAmount("");
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Payment failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Record Fee Payment (Cash/Cheque)" open={open} onClose={onClose}>
      <div className="space-y-4">
        <Field label="Student" required>
          {student ? (
            <div className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-2.5 text-sm font-bold">
              {student.first_name} {student.last_name} ({student.admission_number})
              <button className="text-rose-600 hover:underline" onClick={() => setStudent(null)}>
                Change
              </button>
            </div>
          ) : (
            <>
              <TextInput
                placeholder="Search name or admission no…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {options.length > 0 && (
                <ul className="border border-slate-200 rounded-xl divide-y divide-slate-100 max-h-40 overflow-y-auto">
                  {options.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        className="w-full text-left px-4 py-2 text-sm font-semibold hover:bg-indigo-50"
                        onClick={() => {
                          setStudent(s);
                          setOptions([]);
                        }}
                      >
                        {s.first_name} {s.last_name} · {s.admission_number} ·{" "}
                        {classNameOf(lookups, s.class_id)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Field>
        <Field label="Fee head" required>
          <Select value={structureId} onChange={(e) => setStructureId(Number(e.target.value))} disabled={!student}>
            <option value="">Select…</option>
            {structures.map((s) => (
              <option key={s.id} value={s.id}>
                {s.fee_head} {s.term ? `(${s.term})` : ""} — {rupees(s.amount)}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Amount (₹)" required>
            <TextInput type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
          <Field label="Mode" required>
            <Select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="cash">Cash</option>
              <option value="cheque">Cheque</option>
            </Select>
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={pay} disabled={busy}>
            {busy ? "Recording…" : "Record & Print Receipt"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/* ── Defaulters ──────────────────────────────────────────────────── */

function DefaultersTab({ lookups }: { lookups: Lookups }) {
  const toast = useToast();
  const [defaulters, setDefaulters] = useState<Defaulter[]>([]);
  const [loading, setLoading] = useState(true);
  const [classFilter, setClassFilter] = useState<number | "">("");

  useEffect(() => {
    setLoading(true);
    const params = classFilter === "" ? "" : `?class_id=${classFilter}`;
    authFetch<Defaulter[]>(`/api/fees/defaulters${params}`)
      .then(setDefaulters)
      .catch((error) => toast(error instanceof Error ? error.message : "Failed", "error"))
      .finally(() => setLoading(false));
  }, [classFilter, toast]);

  const columns: Column<Defaulter>[] = [
    { header: "Student", render: (d) => `${d.student_name} (${d.admission_number})` },
    { header: "Class", render: (d) => d.class_name },
    { header: "Fee Head", render: (d) => d.fee_head },
    { header: "Due", render: (d) => rupees(d.amount_due) },
    { header: "Paid", render: (d) => rupees(d.amount_paid) },
    {
      header: "Balance",
      render: (d) => <span className="text-rose-600 font-extrabold">{rupees(d.balance)}</span>,
    },
    { header: "Due Date", render: (d) => formatDate(d.due_date) },
  ];

  const totalOutstanding = defaulters.reduce((sum, d) => sum + d.balance, 0);

  return (
    <>
      <div className="flex items-center gap-3">
        <Select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value === "" ? "" : Number(e.target.value))}
          className="max-w-[180px]"
        >
          <option value="">All classes</option>
          {lookups.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <p className="ml-auto text-sm font-bold text-slate-600">
          Total outstanding: <span className="text-rose-600">{rupees(totalOutstanding)}</span>
        </p>
        <Button
          variant="secondary"
          disabled={defaulters.length === 0}
          onClick={() =>
            downloadFile(
              `/api/fees/defaulters/export.csv${classFilter !== "" ? `?class_id=${classFilter}` : ""}`,
              "defaulters.csv",
            ).catch((error) => toast(error instanceof Error ? error.message : "Failed", "error"))
          }
        >
          Export CSV
        </Button>
        <Button
          variant="secondary"
          disabled={defaulters.length === 0}
          onClick={async () => {
            if (!confirm("Send WhatsApp fee reminders to all defaulters' parents?")) return;
            try {
              const result = await authFetch<{ message: string }>("/api/fees/reminders/dispatch", {
                method: "POST",
              });
              toast(result.message);
            } catch (error) {
              toast(error instanceof Error ? error.message : "Failed", "error");
            }
          }}
        >
          Send WhatsApp Reminders
        </Button>
      </div>
      <DataTable
        columns={columns}
        rows={defaulters}
        keyFor={(d) => `${d.student_id}-${d.fee_head}-${d.due_date}`}
        loading={loading}
        empty="No defaulters — everyone has paid 🎉"
      />
    </>
  );
}

export default function AdminFees() {
  return (
    <PortalShell portal="admin" title="Fee Management">
      <FeesPage />
    </PortalShell>
  );
}

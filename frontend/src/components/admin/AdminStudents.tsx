import { useCallback, useEffect, useState } from "react";
import { authFetch, downloadFile, openHtmlDocument } from "../../lib/api";
import {
  getLookups,
  classNameOf,
  sectionNameOf,
  sectionsForClass,
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
  TextArea,
  TextInput,
  useDebounced,
  useToast,
  type Column,
} from "../portal/kit";

interface ParentInfo {
  id?: number;
  name: string;
  phone: string;
  email: string | null;
  whatsapp_number?: string | null;
  relation: string;
}

interface Student {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  dob: string;
  gender: string;
  photo_url: string | null;
  class_id: number;
  section_id: number;
  roll_number: number | null;
  address: string | null;
  is_active: boolean;
  parents: ParentInfo[];
}

interface StudentList {
  items: Student[];
  total: number;
  page: number;
  total_pages: number;
}

interface FormState {
  first_name: string;
  last_name: string;
  dob: string;
  gender: string;
  class_id: number | "";
  section_id: number | "";
  roll_number: string;
  address: string;
  parent_name: string;
  parent_phone: string;
  parent_relation: string;
}

const emptyForm: FormState = {
  first_name: "",
  last_name: "",
  dob: "",
  gender: "male",
  class_id: "",
  section_id: "",
  roll_number: "",
  address: "",
  parent_name: "",
  parent_phone: "",
  parent_relation: "father",
};

function StudentsPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [list, setList] = useState<StudentList | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState<number | "">("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounced(search);

  const [editing, setEditing] = useState<Student | "new" | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [promoteOpen, setPromoteOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (classFilter !== "") params.set("class_id", String(classFilter));
      setList(await authFetch<StudentList>(`/api/students/?${params}`));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load students", "error");
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, classFilter, toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load classes", "error"));
    // Pre-fill from an admitted enquiry ("Convert to Student").
    if (new URLSearchParams(location.search).get("new") === "1") {
      const raw = localStorage.getItem("student_prefill");
      if (raw) {
        localStorage.removeItem("student_prefill");
        try {
          const prefill = JSON.parse(raw);
          setForm({ ...emptyForm, ...prefill });
          setEditing("new");
        } catch {
          /* ignore malformed prefill */
        }
      }
    }
  }, [toast]);
  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setForm(emptyForm);
    setEditing("new");
  };

  const openEdit = (student: Student) => {
    setForm({
      first_name: student.first_name,
      last_name: student.last_name,
      dob: student.dob,
      gender: student.gender,
      class_id: student.class_id,
      section_id: student.section_id,
      roll_number: student.roll_number ? String(student.roll_number) : "",
      address: student.address ?? "",
      parent_name: student.parents[0]?.name ?? "",
      parent_phone: student.parents[0]?.phone ?? "",
      parent_relation: student.parents[0]?.relation ?? "father",
    });
    setEditing(student);
  };

  const save = async () => {
    if (!form.first_name || !form.dob || form.class_id === "" || form.section_id === "") {
      toast("Name, date of birth, class and section are required", "error");
      return;
    }
    setSaving(true);
    try {
      if (editing === "new") {
        await authFetch("/api/students/", {
          method: "POST",
          body: {
            first_name: form.first_name,
            last_name: form.last_name,
            dob: form.dob,
            gender: form.gender,
            class_id: form.class_id,
            section_id: form.section_id,
            roll_number: form.roll_number ? Number(form.roll_number) : null,
            address: form.address || null,
            parents:
              form.parent_name && form.parent_phone
                ? [
                    {
                      name: form.parent_name,
                      phone: form.parent_phone,
                      relation: form.parent_relation,
                    },
                  ]
                : [],
          },
        });
        toast("Student created");
      } else if (editing) {
        await authFetch(`/api/students/${editing.id}`, {
          method: "PUT",
          body: {
            first_name: form.first_name,
            last_name: form.last_name,
            dob: form.dob,
            gender: form.gender,
            class_id: form.class_id,
            section_id: form.section_id,
            roll_number: form.roll_number ? Number(form.roll_number) : null,
            address: form.address || null,
          },
        });
        toast("Student updated");
      }
      setEditing(null);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (student: Student) => {
    if (!confirm(`Deactivate ${student.first_name} ${student.last_name}?`)) return;
    try {
      await authFetch(`/api/students/${student.id}`, { method: "DELETE" });
      toast("Student deactivated");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const openTC = async (student: Student) => {
    try {
      await openHtmlDocument(`/api/students/${student.id}/tc`);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not open TC", "error");
    }
  };

  if (!lookups) return <Spinner />;

  const columns: Column<Student>[] = [
    { header: "Adm. No", render: (s) => s.admission_number },
    {
      header: "Name",
      render: (s) => (
        <span className={s.is_active ? "" : "line-through text-slate-400"}>
          {s.first_name} {s.last_name}
        </span>
      ),
    },
    {
      header: "Class",
      render: (s) => `${classNameOf(lookups, s.class_id)} – ${sectionNameOf(lookups, s.section_id)}`,
    },
    { header: "Roll", render: (s) => s.roll_number ?? "—" },
    { header: "Parent Phone", render: (s) => s.parents[0]?.phone ?? "—" },
    {
      header: "Actions",
      render: (s) => (
        <span className="flex gap-2">
          <button className="text-indigo-600 font-bold hover:underline" onClick={() => openEdit(s)}>
            Edit
          </button>
          <button className="text-slate-500 font-bold hover:underline" onClick={() => openTC(s)}>
            TC
          </button>
          <button
            className="text-slate-500 font-bold hover:underline"
            onClick={() =>
              openHtmlDocument(`/api/students/${s.id}/bonafide`).catch((error) =>
                toast(error instanceof Error ? error.message : "Failed", "error"),
              )
            }
          >
            Bonafide
          </button>
          {s.is_active && (
            <button className="text-rose-600 font-bold hover:underline" onClick={() => deactivate(s)}>
              Deactivate
            </button>
          )}
        </span>
      ),
    },
  ];

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <TextInput
          placeholder="Search by name or admission no…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
        <Select
          value={classFilter}
          onChange={(e) => {
            setClassFilter(e.target.value === "" ? "" : Number(e.target.value));
            setPage(1);
          }}
          className="max-w-[160px]"
        >
          <option value="">All classes</option>
          {lookups.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <div className="ml-auto flex gap-2">
          <Button
            variant="secondary"
            onClick={() =>
              downloadFile(
                `/api/students/export.csv${classFilter !== "" ? `?class_id=${classFilter}` : ""}`,
                "students.csv",
              ).catch((error) => toast(error instanceof Error ? error.message : "Failed", "error"))
            }
          >
            Export CSV
          </Button>
          <Button variant="secondary" onClick={() => setPromoteOpen(true)}>
            Promote Class
          </Button>
          <Button variant="secondary" onClick={() => setImportOpen(true)}>
            Bulk Import
          </Button>
          <Button onClick={openCreate}>+ Add Student</Button>
        </div>
      </div>

      <DataTable columns={columns} rows={list?.items ?? []} keyFor={(s) => s.id} loading={loading} />

      {list && list.total_pages > 1 && (
        <div className="flex items-center gap-3 justify-end text-sm font-bold text-slate-600">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            ← Prev
          </Button>
          Page {list.page} of {list.total_pages} ({list.total} students)
          <Button
            variant="secondary"
            disabled={page >= list.total_pages}
            onClick={() => setPage(page + 1)}
          >
            Next →
          </Button>
        </div>
      )}

      {/* Create/Edit modal */}
      <Modal
        title={editing === "new" ? "Add Student" : "Edit Student"}
        open={editing !== null}
        onClose={() => setEditing(null)}
        wide
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="First name" required>
            <TextInput value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </Field>
          <Field label="Last name">
            <TextInput value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </Field>
          <Field label="Date of birth" required>
            <TextInput type="date" value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
          </Field>
          <Field label="Gender" required>
            <Select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </Select>
          </Field>
          <Field label="Class" required>
            <Select
              value={form.class_id}
              onChange={(e) =>
                setForm({ ...form, class_id: Number(e.target.value), section_id: "" })
              }
            >
              <option value="">Select…</option>
              {lookups.classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Section" required>
            <Select
              value={form.section_id}
              onChange={(e) => setForm({ ...form, section_id: Number(e.target.value) })}
            >
              <option value="">Select…</option>
              {sectionsForClass(lookups, form.class_id).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Roll number">
            <TextInput
              type="number"
              value={form.roll_number}
              onChange={(e) => setForm({ ...form, roll_number: e.target.value })}
            />
          </Field>
          <Field label="Address">
            <TextInput value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </Field>
        </div>
        {editing === "new" && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
            <Field label="Parent name">
              <TextInput value={form.parent_name} onChange={(e) => setForm({ ...form, parent_name: e.target.value })} />
            </Field>
            <Field label="Parent phone (WhatsApp)">
              <TextInput value={form.parent_phone} onChange={(e) => setForm({ ...form, parent_phone: e.target.value })} />
            </Field>
            <Field label="Relation">
              <Select
                value={form.parent_relation}
                onChange={(e) => setForm({ ...form, parent_relation: e.target.value })}
              >
                <option value="father">Father</option>
                <option value="mother">Mother</option>
                <option value="guardian">Guardian</option>
              </Select>
            </Field>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={() => setEditing(null)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </Modal>

      <BulkImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        lookups={lookups}
        onDone={() => {
          setImportOpen(false);
          load();
        }}
      />
      <PromoteModal
        open={promoteOpen}
        onClose={() => setPromoteOpen(false)}
        lookups={lookups}
        onDone={() => {
          setPromoteOpen(false);
          load();
        }}
      />
    </>
  );
}

/* ── Bulk import (CSV paste) ─────────────────────────────────────── */

function BulkImportModal({
  open,
  onClose,
  lookups,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  lookups: Lookups;
  onDone: () => void;
}) {
  const toast = useToast();
  const [csv, setCsv] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const run = async () => {
    const lines = csv.trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) {
      toast("Paste CSV with a header row and at least one student", "error");
      return;
    }
    const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
    const need = ["first_name", "dob", "gender", "class", "section"];
    const missing = need.filter((h) => !headers.includes(h));
    if (missing.length) {
      toast(`Missing columns: ${missing.join(", ")}`, "error");
      return;
    }
    const rows = [];
    const errors: string[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(",").map((v) => v.trim());
      const get = (name: string) => values[headers.indexOf(name)] ?? "";
      const cls = lookups.classes.find(
        (c) => c.name.toLowerCase() === get("class").toLowerCase(),
      );
      const section = lookups.sections.find(
        (s) => s.class_id === cls?.id && s.name.toLowerCase() === get("section").toLowerCase(),
      );
      if (!cls || !section) {
        errors.push(`Row ${i}: unknown class/section "${get("class")}-${get("section")}"`);
        continue;
      }
      rows.push({
        first_name: get("first_name"),
        last_name: get("last_name"),
        dob: get("dob"),
        gender: get("gender") || "male",
        class_id: cls.id,
        section_id: section.id,
        roll_number: get("roll_number") ? Number(get("roll_number")) : null,
        address: get("address") || null,
        parents:
          get("parent_name") && get("parent_phone")
            ? [
                {
                  name: get("parent_name"),
                  phone: get("parent_phone"),
                  relation: get("relation") || "father",
                },
              ]
            : [],
      });
    }
    if (errors.length) {
      setResult(errors.join("\n"));
      return;
    }
    setBusy(true);
    try {
      const response = await authFetch<{ imported: number; skipped: number; errors: string[] }>(
        "/api/students/bulk-import",
        { method: "POST", body: rows },
      );
      setResult(
        `Imported ${response.imported}, skipped ${response.skipped}.` +
          (response.errors.length ? `\n${response.errors.join("\n")}` : ""),
      );
      if (response.imported > 0) {
        toast(`Imported ${response.imported} students`);
        onDone();
      }
    } catch (error) {
      toast(error instanceof Error ? error.message : "Import failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Bulk Import Students (CSV)" open={open} onClose={onClose} wide>
      <p className="text-xs text-slate-500 font-semibold">
        Paste CSV rows exported from Excel. Required columns:{" "}
        <code className="bg-slate-100 px-1 rounded">first_name,last_name,dob,gender,class,section</code>{" "}
        — optional: <code className="bg-slate-100 px-1 rounded">roll_number,address,parent_name,parent_phone,relation</code>.
        Dates as YYYY-MM-DD; class/section by name (e.g. "Class 1", "A").
      </p>
      <TextArea
        rows={10}
        value={csv}
        onChange={(e) => setCsv(e.target.value)}
        placeholder={"first_name,last_name,dob,gender,class,section,parent_name,parent_phone\nAarav,Sharma,2019-05-12,male,Class 1,A,Rakesh Sharma,9876543210"}
      />
      {result && (
        <pre className="text-xs bg-slate-50 border border-slate-100 rounded-xl p-3 whitespace-pre-wrap max-h-40 overflow-y-auto">
          {result}
        </pre>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button onClick={run} disabled={busy}>
          {busy ? "Importing…" : "Import"}
        </Button>
      </div>
    </Modal>
  );
}

/* ── Promote class ───────────────────────────────────────────────── */

function PromoteModal({
  open,
  onClose,
  lookups,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  lookups: Lookups;
  onDone: () => void;
}) {
  const toast = useToast();
  const [fromClass, setFromClass] = useState<number | "">("");
  const [toClass, setToClass] = useState<number | "">("");
  const [toSection, setToSection] = useState<number | "">("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (fromClass === "" || toClass === "" || toSection === "") {
      toast("Pick source class, target class and target section", "error");
      return;
    }
    if (
      !confirm(
        `Promote ALL active students of ${classNameOf(lookups, fromClass)} to ${classNameOf(lookups, toClass)}? This cannot be undone in one click.`,
      )
    )
      return;
    setBusy(true);
    try {
      const response = await authFetch<{ promoted: number }>("/api/students/promote", {
        method: "POST",
        body: { from_class_id: fromClass, to_class_id: toClass, to_section_id: toSection },
      });
      toast(`Promoted ${response.promoted} students`);
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Promotion failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Promote Whole Class" open={open} onClose={onClose}>
      <div className="space-y-4">
        <Field label="From class" required>
          <Select value={fromClass} onChange={(e) => setFromClass(Number(e.target.value))}>
            <option value="">Select…</option>
            {lookups.classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="To class" required>
          <Select
            value={toClass}
            onChange={(e) => {
              setToClass(Number(e.target.value));
              setToSection("");
            }}
          >
            <option value="">Select…</option>
            {lookups.classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="To section" required>
          <Select value={toSection} onChange={(e) => setToSection(Number(e.target.value))}>
            <option value="">Select…</option>
            {sectionsForClass(lookups, toClass).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={run} disabled={busy}>
            {busy ? "Promoting…" : "Promote"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function AdminStudents() {
  return (
    <PortalShell portal="admin" title="Student Management">
      <StudentsPage />
    </PortalShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import {
  getLookups,
  classNameOf,
  sectionNameOf,
  sectionsForClass,
  subjectNameOf,
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
  useToast,
  type Column,
} from "../portal/kit";

interface Assignment {
  id: number;
  subject_id: number;
  class_id: number;
  section_id: number;
}

interface Staff {
  id: number;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  qualification: string | null;
  designation: string | null;
  is_active: boolean;
  subject_assignments: Assignment[];
}

interface StaffForm {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  qualification: string;
  designation: string;
}

const emptyForm: StaffForm = {
  first_name: "",
  last_name: "",
  phone: "",
  email: "",
  qualification: "",
  designation: "",
};

function StaffPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Staff | "new" | null>(null);
  const [form, setForm] = useState<StaffForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<Staff | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStaff(await authFetch<Staff[]>("/api/staff/"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load staff", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => toast("Failed to load lookups", "error"));
    load();
  }, [load, toast]);

  const save = async () => {
    if (!form.first_name || !form.phone) {
      toast("Name and phone are required", "error");
      return;
    }
    setSaving(true);
    try {
      const body = {
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone,
        email: form.email || null,
        qualification: form.qualification || null,
        designation: form.designation || null,
      };
      if (editing === "new") {
        await authFetch("/api/staff/", { method: "POST", body });
        toast("Staff member added");
      } else if (editing) {
        await authFetch(`/api/staff/${editing.id}`, { method: "PUT", body });
        toast("Staff member updated");
      }
      setEditing(null);
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (member: Staff) => {
    if (!confirm(`Deactivate ${member.first_name} ${member.last_name}?`)) return;
    try {
      await authFetch(`/api/staff/${member.id}`, { method: "DELETE" });
      toast("Staff member deactivated");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const createLogin = async (member: Staff) => {
    const suggestedId = `EMP-${String(member.id).padStart(3, "0")}`;
    const loginId = prompt(`Login ID for ${member.first_name}:`, suggestedId);
    if (!loginId) return;
    const password = prompt(`Password for ${loginId} (min 8 chars):`);
    if (!password) return;
    try {
      await authFetch("/api/users/", {
        method: "POST",
        body: {
          role: "teacher",
          login_id: loginId.trim(),
          email: member.email,
          phone: member.phone,
          password,
          linked_staff_id: member.id,
        },
      });
      toast(`Login "${loginId.trim()}" created — share the ID and password with ${member.first_name}`);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to create login", "error");
    }
  };

  if (!lookups) return <Spinner />;

  const columns: Column<Staff>[] = [
    {
      header: "Name",
      render: (s) => (
        <span className={s.is_active ? "" : "line-through text-slate-400"}>
          {s.first_name} {s.last_name}
        </span>
      ),
    },
    { header: "Designation", render: (s) => s.designation ?? "—" },
    { header: "Phone", render: (s) => s.phone },
    { header: "Assignments", render: (s) => s.subject_assignments.length },
    {
      header: "Actions",
      render: (s) => (
        <span className="flex gap-2">
          <button
            className="text-indigo-600 font-bold hover:underline"
            onClick={() => setDetail(s)}
          >
            Subjects
          </button>
          <button
            className="text-indigo-600 font-bold hover:underline"
            onClick={() => {
              setForm({
                first_name: s.first_name,
                last_name: s.last_name,
                phone: s.phone,
                email: s.email ?? "",
                qualification: s.qualification ?? "",
                designation: s.designation ?? "",
              });
              setEditing(s);
            }}
          >
            Edit
          </button>
          <button className="text-slate-500 font-bold hover:underline" onClick={() => createLogin(s)}>
            Login
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
      <div className="flex justify-end">
        <Button
          onClick={() => {
            setForm(emptyForm);
            setEditing("new");
          }}
        >
          + Add Staff
        </Button>
      </div>

      <DataTable columns={columns} rows={staff} keyFor={(s) => s.id} loading={loading} />

      <Modal
        title={editing === "new" ? "Add Staff Member" : "Edit Staff Member"}
        open={editing !== null}
        onClose={() => setEditing(null)}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="First name" required>
            <TextInput value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </Field>
          <Field label="Last name">
            <TextInput value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </Field>
          <Field label="Phone" required>
            <TextInput value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </Field>
          <Field label="Email">
            <TextInput value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Qualification">
            <TextInput value={form.qualification} onChange={(e) => setForm({ ...form, qualification: e.target.value })} />
          </Field>
          <Field label="Designation">
            <TextInput value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
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

      {detail && (
        <AssignmentsModal
          member={detail}
          lookups={lookups}
          onClose={() => setDetail(null)}
          onChanged={(updated) => {
            setDetail(updated);
            load();
          }}
        />
      )}
    </>
  );
}

function AssignmentsModal({
  member,
  lookups,
  onClose,
  onChanged,
}: {
  member: Staff;
  lookups: Lookups;
  onClose: () => void;
  onChanged: (updated: Staff) => void;
}) {
  const toast = useToast();
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [classId, setClassId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const [busy, setBusy] = useState(false);

  const add = async () => {
    if (subjectId === "" || classId === "" || sectionId === "") {
      toast("Pick subject, class and section", "error");
      return;
    }
    setBusy(true);
    try {
      const updated = await authFetch<Staff>(`/api/staff/${member.id}/assignments`, {
        method: "POST",
        body: { subject_id: subjectId, class_id: classId, section_id: sectionId },
      });
      toast("Assignment added");
      onChanged(updated);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (assignment: Assignment) => {
    try {
      await authFetch(`/api/staff/${member.id}/assignments/${assignment.id}`, {
        method: "DELETE",
      });
      toast("Assignment removed");
      onChanged({
        ...member,
        subject_assignments: member.subject_assignments.filter((a) => a.id !== assignment.id),
      });
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  return (
    <Modal
      title={`Teaching Assignments — ${member.first_name} ${member.last_name}`}
      open
      onClose={onClose}
      wide
    >
      <ul className="space-y-2">
        {member.subject_assignments.length === 0 && (
          <li className="text-sm text-slate-400 font-semibold">No assignments yet.</li>
        )}
        {member.subject_assignments.map((a) => (
          <li
            key={a.id}
            className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-2.5 text-sm font-semibold"
          >
            <span>
              {subjectNameOf(lookups, a.subject_id)} — {classNameOf(lookups, a.class_id)}{" "}
              {sectionNameOf(lookups, a.section_id)}
            </span>
            <button className="text-rose-600 font-bold hover:underline" onClick={() => remove(a)}>
              Remove
            </button>
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100">
        <Select value={subjectId} onChange={(e) => setSubjectId(Number(e.target.value))}>
          <option value="">Subject…</option>
          {lookups.subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
        <Select
          value={classId}
          onChange={(e) => {
            setClassId(Number(e.target.value));
            setSectionId("");
          }}
        >
          <option value="">Class…</option>
          {lookups.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select value={sectionId} onChange={(e) => setSectionId(Number(e.target.value))}>
          <option value="">Section…</option>
          {sectionsForClass(lookups, classId).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
        <Button onClick={add} disabled={busy}>
          {busy ? "Adding…" : "Add"}
        </Button>
      </div>
    </Modal>
  );
}

export default function AdminStaff() {
  return (
    <PortalShell portal="admin" title="Staff Management">
      <StaffPage />
    </PortalShell>
  );
}

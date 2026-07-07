import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  Field,
  Modal,
  Select,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";

interface PortalUser {
  id: number;
  clerk_id: string;
  email: string | null;
  phone: string | null;
  role: string;
  linked_staff_id: number | null;
  linked_student_id: number | null;
  is_active: boolean;
  provisioned: boolean;
  created_at: string;
}

interface AuditEntry {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

function UsersPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"users" | "audit">("users");
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await authFetch<PortalUser[]>("/api/users/"));
      setAudit(await authFetch<AuditEntry[]>("/api/users/audit-log"));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load users", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const deactivate = async (user: PortalUser) => {
    if (!confirm(`Deactivate this ${user.role} account? They lose access immediately.`)) return;
    try {
      await authFetch(`/api/users/${user.id}/deactivate`, { method: "POST" });
      toast("User deactivated");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const reactivate = async (user: PortalUser) => {
    try {
      await authFetch(`/api/users/${user.id}`, { method: "PUT", body: { is_active: true } });
      toast("User reactivated");
      load();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const resetPassword = async (user: PortalUser) => {
    const password = prompt("New password (min 8 chars):");
    if (!password) return;
    try {
      await authFetch(`/api/users/${user.id}/reset-password`, { method: "POST", body: { password } });
      toast("Password updated");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const userColumns: Column<PortalUser>[] = [
    { header: "ID", render: (u) => u.id },
    { header: "Email / Phone", render: (u) => u.email || u.phone || "—" },
    {
      header: "Role",
      render: (u) => (
        <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-lg text-[10px] font-bold uppercase">
          {u.role.replace("_", " ")}
        </span>
      ),
    },
    {
      header: "Clerk",
      render: (u) =>
        u.provisioned ? (
          <span className="text-emerald-600 font-bold text-xs">Linked</span>
        ) : (
          <span className="text-amber-600 font-bold text-xs">Pending</span>
        ),
    },
    {
      header: "Active",
      render: (u) => (u.is_active ? "Yes" : <span className="text-rose-600 font-bold">No</span>),
    },
    { header: "Created", render: (u) => formatDate(u.created_at) },
    {
      header: "Actions",
      render: (u) => (
        <span className="flex gap-2">
          {u.provisioned && (
            <button className="text-indigo-600 font-bold hover:underline" onClick={() => resetPassword(u)}>
              Reset PW
            </button>
          )}
          {u.is_active ? (
            <button className="text-rose-600 font-bold hover:underline" onClick={() => deactivate(u)}>
              Deactivate
            </button>
          ) : (
            <button className="text-emerald-600 font-bold hover:underline" onClick={() => reactivate(u)}>
              Reactivate
            </button>
          )}
        </span>
      ),
    },
  ];

  const auditColumns: Column<AuditEntry>[] = [
    { header: "When", render: (a) => new Date(a.created_at).toLocaleString("en-IN") },
    { header: "By user", render: (a) => a.user_id ?? "—" },
    { header: "Action", render: (a) => a.action },
    {
      header: "Target",
      render: (a) => (a.entity_type ? `${a.entity_type} #${a.entity_id ?? ""}` : "—"),
    },
    {
      header: "Detail",
      render: (a) => (a.detail ? JSON.stringify(a.detail) : "—"),
      className: "max-w-[280px] truncate",
    },
  ];

  return (
    <>
      <div className="flex gap-2">
        {(
          [
            ["users", "Users"],
            ["audit", "Audit Trail"],
          ] as const
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
        {tab === "users" && (
          <Button className="ml-auto" onClick={() => setCreateOpen(true)}>
            + Create Login
          </Button>
        )}
      </div>

      {tab === "users" ? (
        <DataTable columns={userColumns} rows={users} keyFor={(u) => u.id} loading={loading} />
      ) : (
        <DataTable
          columns={auditColumns}
          rows={audit}
          keyFor={(a) => a.id}
          loading={loading}
          empty="No admin actions recorded yet."
        />
      )}

      <CreateUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onDone={() => {
          setCreateOpen(false);
          load();
        }}
      />
    </>
  );
}

function CreateUserModal({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [form, setForm] = useState({
    role: "office_admin",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    username: "",
    password: "",
    linked_staff_id: "",
    linked_student_id: "",
  });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (form.password && form.password.length < 8) {
      toast("Password must be at least 8 characters", "error");
      return;
    }
    setBusy(true);
    try {
      const user = await authFetch<PortalUser>("/api/users/", {
        method: "POST",
        body: {
          role: form.role,
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email || null,
          phone: form.phone || null,
          username: form.username || null,
          password: form.password || null,
          linked_staff_id: form.linked_staff_id ? Number(form.linked_staff_id) : null,
          linked_student_id: form.linked_student_id ? Number(form.linked_student_id) : null,
        },
      });
      toast(
        user.provisioned
          ? "Login created in Clerk"
          : "Login saved — will sync to Clerk once keys are configured",
      );
      onDone();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Create Login" open={open} onClose={onClose}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Role" required>
          <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="office_admin">Office Admin Staff</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
            <option value="super_admin">Super Admin</option>
          </Select>
        </Field>
        <Field label="Username (students: admission no)">
          <TextInput value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </Field>
        <Field label="First name">
          <TextInput value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        </Field>
        <Field label="Last name">
          <TextInput value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </Field>
        <Field label="Email">
          <TextInput value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Phone">
          <TextInput value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Password (min 8)">
          <TextInput
            type="text"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        <Field label="Link to staff ID / student ID">
          <div className="flex gap-2">
            <TextInput
              placeholder="Staff #"
              value={form.linked_staff_id}
              onChange={(e) => setForm({ ...form, linked_staff_id: e.target.value })}
            />
            <TextInput
              placeholder="Student #"
              value={form.linked_student_id}
              onChange={(e) => setForm({ ...form, linked_student_id: e.target.value })}
            />
          </div>
        </Field>
      </div>
      <p className="text-xs text-slate-400 font-semibold">
        Teachers should be linked to their staff record and students to their student record — that's
        what scopes their portal to their own data.
      </p>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} disabled={busy}>
          {busy ? "Creating…" : "Create"}
        </Button>
      </div>
    </Modal>
  );
}

export default function AdminUsers() {
  return (
    <PortalShell portal="admin" title="Users & Roles">
      <UsersPage />
    </PortalShell>
  );
}

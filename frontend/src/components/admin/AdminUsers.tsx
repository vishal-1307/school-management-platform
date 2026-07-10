import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import {
  Button,
  DataTable,
  Field,
  Modal,
  rowActionClass,
  Select,
  TextInput,
  formatDate,
  useToast,
  type Column,
} from "../portal/kit";

interface PortalUser {
  id: number;
  login_id: string;
  email: string | null;
  phone: string | null;
  role: string;
  linked_staff_id: number | null;
  linked_student_id: number | null;
  is_active: boolean;
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
    const password = prompt(`New password for ${user.login_id} (min 8 chars):`);
    if (!password) return;
    try {
      await authFetch(`/api/users/${user.id}/reset-password`, { method: "POST", body: { password } });
      toast(`Password updated — share it with ${user.login_id} securely`);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  const userColumns: Column<PortalUser>[] = [
    { header: "Login ID", render: (u) => <span className="font-mono">{u.login_id}</span> },
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
      header: "Active",
      render: (u) => (u.is_active ? "Yes" : <span className="text-rose-600 font-bold">No</span>),
    },
    { header: "Created", className: "whitespace-nowrap", render: (u) => formatDate(u.created_at) },
    {
      header: "Actions",
      className: "whitespace-nowrap",
      render: (u) => (
        <span className="flex flex-wrap gap-0.5 -mx-2">
          <button className={rowActionClass()} onClick={() => resetPassword(u)}>
            Reset PW
          </button>
          {u.is_active ? (
            <button className={rowActionClass("rose")} onClick={() => deactivate(u)}>
              Deactivate
            </button>
          ) : (
            <button
              className="px-2 py-2.5 rounded-lg font-bold text-sm text-emerald-600 hover:underline hover:bg-emerald-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
              onClick={() => reactivate(u)}
            >
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
            className={`px-4 py-2 rounded-xl text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
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
        <DataTable columns={userColumns} rows={users} keyFor={(u) => u.id} loading={loading} stickyLast />
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
    login_id: "",
    email: "",
    phone: "",
    password: "",
    linked_staff_id: "",
    linked_student_id: "",
  });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!form.login_id.trim()) {
      toast("Login ID is required", "error");
      return;
    }
    if (form.password.length < 8) {
      toast("Password must be at least 8 characters", "error");
      return;
    }
    setBusy(true);
    try {
      await authFetch<PortalUser>("/api/users/", {
        method: "POST",
        body: {
          role: form.role,
          login_id: form.login_id.trim(),
          password: form.password,
          email: form.email || null,
          phone: form.phone || null,
          linked_staff_id: form.linked_staff_id ? Number(form.linked_staff_id) : null,
          linked_student_id: form.linked_student_id ? Number(form.linked_student_id) : null,
        },
      });
      toast(`Login "${form.login_id.trim()}" created`);
      setForm({
        role: "office_admin",
        login_id: "",
        email: "",
        phone: "",
        password: "",
        linked_staff_id: "",
        linked_student_id: "",
      });
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
        <Field label="Login ID" required>
          <TextInput
            placeholder="e.g. EMP-004 or ADM-00011"
            value={form.login_id}
            onChange={(e) => setForm({ ...form, login_id: e.target.value })}
          />
        </Field>
        <Field label="Password" required>
          <TextInput
            type="text"
            placeholder="Min 8 characters"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        <Field label="Email">
          <TextInput type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Phone">
          <TextInput type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
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
        what scopes their portal to their own data. Login IDs are usually the admission number
        (students) or an employee ID (staff) — prefer using the "Login" action from Student/Staff
        Management, which pre-fills this for you.
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

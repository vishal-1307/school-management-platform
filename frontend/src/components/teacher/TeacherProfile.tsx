import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import ChangePasswordForm from "../portal/ChangePasswordForm";
import { Button, ErrorNote, Field, Spinner, TextInput, useToast } from "../portal/kit";
import { useTeacherRecord, type TeacherRecord } from "./useTeacher";

function ProfileView() {
  const toast = useToast();
  const { staff, error } = useTeacherRecord();
  const [form, setForm] = useState<Partial<TeacherRecord> | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (staff) setForm(staff);
  }, [staff]);

  if (error) return <ErrorNote message={error} />;
  if (!staff || !form) return <Spinner />;

  const save = async () => {
    setBusy(true);
    try {
      await authFetch("/api/staff/me", {
        method: "PUT",
        body: {
          phone: form.phone,
          email: form.email || null,
          photo_url: form.photo_url || null,
          qualification: form.qualification || null,
        },
      });
      toast("Profile updated");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4 max-w-2xl">
      <div className="flex items-center gap-4">
        <img
          src={
            staff.photo_url ??
            `https://ui-avatars.com/api/?background=eef2ff&color=4f46e5&size=128&name=${encodeURIComponent(`${staff.first_name} ${staff.last_name}`)}`
          }
          alt=""
          className="w-16 h-16 rounded-full object-cover border border-slate-100"
        />
        <div>
          <p className="font-extrabold text-slate-900 text-lg">
            {staff.first_name} {staff.last_name}
          </p>
          <p className="text-sm text-slate-500 font-semibold">{staff.designation ?? "Teacher"}</p>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Phone">
          <TextInput value={form.phone ?? ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Email">
          <TextInput value={form.email ?? ""} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Qualification">
          <TextInput
            value={form.qualification ?? ""}
            onChange={(e) => setForm({ ...form, qualification: e.target.value })}
          />
        </Field>
        <Field label="Photo URL">
          <TextInput
            value={form.photo_url ?? ""}
            onChange={(e) => setForm({ ...form, photo_url: e.target.value })}
          />
        </Field>
      </div>
      <div className="flex justify-end">
        <Button onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </section>
    <ChangePasswordForm />
    </>
  );
}

export default function TeacherProfile() {
  return (
    <PortalShell portal="teacher" title="My Profile">
      <ProfileView />
    </PortalShell>
  );
}

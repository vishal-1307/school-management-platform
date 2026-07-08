import { useState } from "react";
import { authFetch } from "../../lib/api";
import { storeSession } from "../../lib/authStore";
import { Button, Field, TextInput, useToast } from "./kit";

/** Self-service "change my password" — used on Teacher/Student profile pages. */
export default function ChangePasswordForm() {
  const toast = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (newPassword.length < 8) {
      toast("New password must be at least 8 characters", "error");
      return;
    }
    if (newPassword !== confirm) {
      toast("New password and confirmation don't match", "error");
      return;
    }
    setBusy(true);
    try {
      const response = await authFetch<{ token: string }>("/api/auth/change-password", {
        method: "POST",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      storeSession(response.token);
      toast("Password changed");
      setCurrentPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to change password", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4 max-w-2xl">
      <h2 className="font-extrabold text-slate-800">Change Password</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Field label="Current password" required>
          <TextInput
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
        </Field>
        <Field label="New password" required>
          <TextInput type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
        </Field>
        <Field label="Confirm new password" required>
          <TextInput type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
      </div>
      <div className="flex justify-end">
        <Button onClick={submit} disabled={busy}>
          {busy ? "Updating…" : "Change Password"}
        </Button>
      </div>
    </section>
  );
}

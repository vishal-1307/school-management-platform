import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { Button, Field, Select, Spinner, TextArea, TextInput, useToast } from "../portal/kit";

interface SchoolProfile {
  name: string;
  logo_url: string | null;
  address: string | null;
  affiliation_number: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  settings: Record<string, unknown> | null;
}

interface Automation {
  absent_alerts: boolean;
  fee_reminders: boolean;
  notice_broadcast: boolean;
  results_notification: boolean;
}

const AUTOMATION_LABELS: Record<keyof Automation, [string, string]> = {
  absent_alerts: ["Absence WhatsApp alerts", "Message the parent when a student is marked absent"],
  fee_reminders: ["Fee due reminders", "Allow the manual 'Send reminders' action on defaulters"],
  notice_broadcast: ["Notice broadcasts", "Allow sending notices to all parents on WhatsApp"],
  results_notification: ["Results notifications", "Message parents when exam results are published"],
};

function SettingsPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [school, setSchool] = useState<SchoolProfile | null>(null);
  const [automation, setAutomation] = useState<Automation | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [profile, auto, lk] = await Promise.all([
        authFetch<SchoolProfile>("/api/settings/school"),
        authFetch<Automation>("/api/settings/automation"),
        getLookups(true),
      ]);
      setSchool(profile);
      setAutomation(auto);
      setLookups(lk);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load settings", "error");
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const saveSchool = async () => {
    if (!school) return;
    setSaving(true);
    try {
      await authFetch("/api/settings/school", { method: "PUT", body: school });
      toast("School profile saved");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const toggleAutomation = async (key: keyof Automation) => {
    if (!automation) return;
    const next = { ...automation, [key]: !automation[key] };
    setAutomation(next);
    try {
      await authFetch("/api/settings/automation", { method: "PUT", body: next });
      toast("Automation settings saved");
    } catch (error) {
      setAutomation(automation);
      toast(error instanceof Error ? error.message : "Save failed", "error");
    }
  };

  if (!school || !automation || !lookups) return <Spinner />;

  return (
    <>
      {/* School profile */}
      <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
        <h2 className="font-extrabold text-slate-800">School Profile</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="School name" required>
            <TextInput value={school.name} onChange={(e) => setSchool({ ...school, name: e.target.value })} />
          </Field>
          <Field label="Affiliation number">
            <TextInput
              value={school.affiliation_number ?? ""}
              onChange={(e) => setSchool({ ...school, affiliation_number: e.target.value })}
            />
          </Field>
          <Field label="Contact email">
            <TextInput
              value={school.contact_email ?? ""}
              onChange={(e) => setSchool({ ...school, contact_email: e.target.value })}
            />
          </Field>
          <Field label="Contact phone">
            <TextInput
              value={school.contact_phone ?? ""}
              onChange={(e) => setSchool({ ...school, contact_phone: e.target.value })}
            />
          </Field>
          <Field label="Logo URL">
            <TextInput
              value={school.logo_url ?? ""}
              onChange={(e) => setSchool({ ...school, logo_url: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Address">
          <TextArea
            rows={2}
            value={school.address ?? ""}
            onChange={(e) => setSchool({ ...school, address: e.target.value })}
          />
        </Field>
        <div className="flex justify-end">
          <Button onClick={saveSchool} disabled={saving}>
            {saving ? "Saving…" : "Save Profile"}
          </Button>
        </div>
      </section>

      {/* Automation toggles */}
      <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
        <h2 className="font-extrabold text-slate-800">Automation (SRS 6.14)</h2>
        <p className="text-xs text-slate-500 font-semibold">
          These control the WhatsApp automations. Until WhatsApp credentials are configured, actions
          run in "skipped" mode and appear in the Communication Log without sending anything.
        </p>
        {(Object.keys(AUTOMATION_LABELS) as (keyof Automation)[]).map((key) => (
          <label key={key} className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-1"
              checked={automation[key]}
              onChange={() => toggleAutomation(key)}
            />
            <span>
              <span className="block text-sm font-bold text-slate-700">{AUTOMATION_LABELS[key][0]}</span>
              <span className="block text-xs text-slate-500 font-semibold">{AUTOMATION_LABELS[key][1]}</span>
            </span>
          </label>
        ))}
      </section>

      <AcademicSetup lookups={lookups} onChanged={load} />
    </>
  );
}

function AcademicSetup({ lookups, onChanged }: { lookups: Lookups; onChanged: () => void }) {
  const toast = useToast();
  const [className, setClassName] = useState("");
  const [sectionName, setSectionName] = useState("");
  const [sectionClassId, setSectionClassId] = useState<number | "">("");
  const [subjectName, setSubjectName] = useState("");
  const [subjectCode, setSubjectCode] = useState("");
  const [yearLabel, setYearLabel] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");

  const post = async (path: string, body: unknown, label: string) => {
    try {
      await authFetch(path, { method: "POST", body });
      toast(`${label} added`);
      onChanged();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed", "error");
    }
  };

  return (
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-6">
      <h2 className="font-extrabold text-slate-800">Academic Setup (SRS 6.16)</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Classes ({lookups.classes.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {lookups.classes.map((c) => (
              <span key={c.id} className="px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-bold text-slate-600">
                {c.name}
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <TextInput placeholder="New class name" value={className} onChange={(e) => setClassName(e.target.value)} />
            <Button
              variant="secondary"
              onClick={() =>
                className &&
                post(
                  "/api/settings/classes",
                  { name: className, numeric_order: lookups.classes.length + 1 },
                  "Class",
                ).then(() => setClassName(""))
              }
            >
              Add
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Sections ({lookups.sections.length})
          </p>
          <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
            {lookups.sections.map((s) => (
              <span key={s.id} className="px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-bold text-slate-600">
                {classNameOf(lookups, s.class_id)}-{s.name}
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <Select value={sectionClassId} onChange={(e) => setSectionClassId(Number(e.target.value))}>
              <option value="">Class…</option>
              {lookups.classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
            <TextInput
              placeholder="e.g. B"
              value={sectionName}
              onChange={(e) => setSectionName(e.target.value)}
              className="max-w-[80px]"
            />
            <Button
              variant="secondary"
              onClick={() =>
                sectionName &&
                sectionClassId !== "" &&
                post(
                  "/api/settings/sections",
                  { name: sectionName, class_id: sectionClassId },
                  "Section",
                ).then(() => setSectionName(""))
              }
            >
              Add
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Subjects ({lookups.subjects.length})
          </p>
          <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
            {lookups.subjects.map((s) => (
              <span key={s.id} className="px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-bold text-slate-600">
                {s.name}
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <TextInput placeholder="Subject name" value={subjectName} onChange={(e) => setSubjectName(e.target.value)} />
            <TextInput
              placeholder="Code"
              value={subjectCode}
              onChange={(e) => setSubjectCode(e.target.value)}
              className="max-w-[110px]"
            />
            <Button
              variant="secondary"
              onClick={() =>
                subjectName &&
                subjectCode &&
                post("/api/settings/subjects", { name: subjectName, code: subjectCode }, "Subject").then(
                  () => {
                    setSubjectName("");
                    setSubjectCode("");
                  },
                )
              }
            >
              Add
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Academic years</p>
          <div className="flex flex-wrap gap-1.5">
            {lookups.years.map((y) => (
              <span
                key={y.id}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold ${
                  y.is_current ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"
                }`}
              >
                {y.label}
                {y.is_current ? " (current)" : ""}
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <TextInput
              placeholder="2027-28"
              value={yearLabel}
              onChange={(e) => setYearLabel(e.target.value)}
              className="max-w-[110px]"
            />
            <TextInput type="date" value={yearStart} onChange={(e) => setYearStart(e.target.value)} />
            <TextInput type="date" value={yearEnd} onChange={(e) => setYearEnd(e.target.value)} />
            <Button
              variant="secondary"
              onClick={() =>
                yearLabel &&
                yearStart &&
                yearEnd &&
                post(
                  "/api/settings/academic-years",
                  { label: yearLabel, start_date: yearStart, end_date: yearEnd, is_current: false },
                  "Academic year",
                ).then(() => setYearLabel(""))
              }
            >
              Add
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function AdminSettings() {
  return (
    <PortalShell portal="admin" title="School Settings">
      <SettingsPage />
    </PortalShell>
  );
}

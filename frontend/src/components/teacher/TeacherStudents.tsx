import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import { getLookups, classNameOf, sectionNameOf, type Lookups } from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { DataTable, ErrorNote, Field, Select, Spinner, useToast, type Column } from "../portal/kit";
import { useTeacherRecord, classSections } from "./useTeacher";

interface StudentLite {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  roll_number: number | null;
  dob: string;
  parents: { name: string; phone: string; relation: string }[];
}

function StudentsView() {
  const toast = useToast();
  const { staff, error } = useTeacherRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [pair, setPair] = useState("");
  const [students, setStudents] = useState<StudentLite[]>([]);
  const [loading, setLoading] = useState(false);

  const pairs = classSections(staff);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
  }, []);
  useEffect(() => {
    if (!pair && pairs.length > 0) setPair(`${pairs[0].class_id}-${pairs[0].section_id}`);
  }, [pairs, pair]);

  useEffect(() => {
    if (!pair) return;
    const [classId, sectionId] = pair.split("-").map(Number);
    setLoading(true);
    authFetch<{ items: StudentLite[] }>(
      `/api/students/?class_id=${classId}&section_id=${sectionId}&page_size=100`,
    )
      .then((r) => setStudents(r.items))
      .catch((e) => toast(e instanceof Error ? e.message : "Failed to load", "error"))
      .finally(() => setLoading(false));
  }, [pair, toast]);

  if (error) return <ErrorNote message={error} />;
  if (!staff || !lookups) return <Spinner />;
  if (pairs.length === 0) return <ErrorNote message="No classes assigned to you yet." />;

  const columns: Column<StudentLite>[] = [
    { header: "Roll", render: (s) => s.roll_number ?? "—" },
    { header: "Name", render: (s) => `${s.first_name} ${s.last_name}` },
    { header: "Adm. No", render: (s) => s.admission_number },
    { header: "Parent", render: (s) => s.parents[0]?.name ?? "—" },
    { header: "Parent Phone", render: (s) => s.parents[0]?.phone ?? "—" },
  ];

  return (
    <>
      <p className="text-sm text-slate-500 font-semibold">
        Read-only view of students in your classes (SRS 7.6) — no fee or other personal data.
      </p>
      <Field label="Class">
        <Select value={pair} onChange={(e) => setPair(e.target.value)} className="max-w-[200px]">
          {pairs.map((p) => (
            <option key={`${p.class_id}-${p.section_id}`} value={`${p.class_id}-${p.section_id}`}>
              {classNameOf(lookups, p.class_id)} {sectionNameOf(lookups, p.section_id)}
            </option>
          ))}
        </Select>
      </Field>
      <DataTable columns={columns} rows={students} keyFor={(s) => s.id} loading={loading} />
    </>
  );
}

export default function TeacherStudents() {
  return (
    <PortalShell portal="teacher" title="My Students">
      <StudentsView />
    </PortalShell>
  );
}

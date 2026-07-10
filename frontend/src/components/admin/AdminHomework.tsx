import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import {
  getLookups,
  classNameOf,
  sectionNameOf,
  subjectNameOf,
  type Lookups,
} from "../../lib/lookups";
import PortalShell from "../portal/PortalShell";
import { DataTable, Select, Spinner, formatDate, useToast, type Column } from "../portal/kit";

interface Homework {
  id: number;
  class_id: number;
  section_id: number;
  subject_id: number;
  assigned_by_id: number;
  title: string;
  description: string | null;
  attachment_url: string | null;
  due_date: string;
  created_at: string;
}

function HomeworkPage() {
  const toast = useToast();
  const [lookups, setLookups] = useState<Lookups | null>(null);
  const [homework, setHomework] = useState<Homework[]>([]);
  const [loading, setLoading] = useState(true);
  const [classFilter, setClassFilter] = useState<number | "">("");
  const [subjectFilter, setSubjectFilter] = useState<number | "">("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (classFilter !== "") params.set("class_id", String(classFilter));
      if (subjectFilter !== "") params.set("subject_id", String(subjectFilter));
      setHomework(await authFetch<Homework[]>(`/api/homework/?${params}`));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to load homework", "error");
    } finally {
      setLoading(false);
    }
  }, [classFilter, subjectFilter, toast]);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
    load();
  }, [load]);

  if (!lookups) return <Spinner />;

  const columns: Column<Homework>[] = [
    { header: "Title", render: (h) => h.title },
    {
      header: "Class",
      render: (h) => `${classNameOf(lookups, h.class_id)} ${sectionNameOf(lookups, h.section_id)}`,
    },
    { header: "Subject", render: (h) => subjectNameOf(lookups, h.subject_id) },
    { header: "Assigned", render: (h) => formatDate(h.created_at) },
    { header: "Due", render: (h) => formatDate(h.due_date) },
    {
      header: "Attachment",
      render: (h) =>
        h.attachment_url ? (
          <a href={h.attachment_url} target="_blank" rel="noopener" className="text-indigo-600 font-bold hover:underline">
            Open
          </a>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <>
      <p className="text-sm text-slate-500 font-semibold">
        Oversight of everything teachers have assigned. Teachers post homework from their
        own portal.
      </p>
      <div className="flex gap-3">
        <Select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value === "" ? "" : Number(e.target.value))}
          className="max-w-[160px]"
        >
          <option value="">All classes</option>
          {lookups.classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value === "" ? "" : Number(e.target.value))}
          className="max-w-[180px]"
        >
          <option value="">All subjects</option>
          {lookups.subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
      </div>
      <DataTable
        columns={columns}
        rows={homework}
        keyFor={(h) => h.id}
        loading={loading}
        empty="No homework posted for this filter — worth checking with the class teachers."
      />
    </>
  );
}

export default function AdminHomework() {
  return (
    <PortalShell portal="admin" title="Homework Oversight">
      <HomeworkPage />
    </PortalShell>
  );
}

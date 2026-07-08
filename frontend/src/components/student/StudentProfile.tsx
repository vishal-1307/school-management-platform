import PortalShell from "../portal/PortalShell";
import ChangePasswordForm from "../portal/ChangePasswordForm";
import { ErrorNote, Spinner, formatDate } from "../portal/kit";
import { useStudentRecord } from "./useStudent";
import { useEffect, useState } from "react";
import { getLookups, classNameOf, sectionNameOf, type Lookups } from "../../lib/lookups";

function ProfileView() {
  const { student, error } = useStudentRecord();
  const [lookups, setLookups] = useState<Lookups | null>(null);

  useEffect(() => {
    getLookups().then(setLookups).catch(() => {});
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!student || !lookups) return <Spinner />;

  const rows: [string, string][] = [
    ["Name", `${student.first_name} ${student.last_name}`],
    ["Admission number", student.admission_number],
    ["Class", `${classNameOf(lookups, student.class_id)} ${sectionNameOf(lookups, student.section_id)}`],
    ["Roll number", student.roll_number !== null ? String(student.roll_number) : "—"],
    ["Date of birth", formatDate(student.dob)],
    ["Gender", student.gender],
    ["Address", student.address ?? "—"],
  ];

  return (
    <>
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-5 max-w-2xl">
      <div className="flex items-center gap-4">
        <img
          src={
            student.photo_url ??
            `https://ui-avatars.com/api/?background=eef2ff&color=4f46e5&size=128&name=${encodeURIComponent(`${student.first_name} ${student.last_name}`)}`
          }
          alt=""
          className="w-16 h-16 rounded-full object-cover border border-slate-100"
        />
        <div>
          <p className="font-extrabold text-slate-900 text-lg">
            {student.first_name} {student.last_name}
          </p>
          <p className="text-sm text-slate-500 font-semibold">{student.admission_number}</p>
        </div>
      </div>
      <dl className="divide-y divide-slate-50">
        {rows.map(([label, value]) => (
          <div key={label} className="flex py-2.5 text-sm">
            <dt className="w-44 font-bold text-slate-400">{label}</dt>
            <dd className="font-semibold text-slate-700">{value}</dd>
          </div>
        ))}
        {student.parents.map((parent, i) => (
          <div key={i} className="flex py-2.5 text-sm">
            <dt className="w-44 font-bold text-slate-400 capitalize">{parent.relation}</dt>
            <dd className="font-semibold text-slate-700">
              {parent.name} · {parent.phone}
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-slate-400 font-semibold">
        Spot a mistake? Official records can only be corrected by the school office — contact them
        with the right details (SRS 8.8).
      </p>
    </section>
    <ChangePasswordForm />
    </>
  );
}

export default function StudentProfile() {
  return (
    <PortalShell portal="student" title="My Profile">
      <ProfileView />
    </PortalShell>
  );
}

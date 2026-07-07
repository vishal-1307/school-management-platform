import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Spinner, formatDate, useToast } from "../portal/kit";
import { useStudentRecord } from "./useStudent";

interface Notice {
  id: number;
  title: string;
  content: string;
  attachment_url: string | null;
  audience: string;
  target_class_id: number | null;
  published_at: string | null;
}

function NoticesView() {
  const toast = useToast();
  const { student } = useStudentRecord();
  const [notices, setNotices] = useState<Notice[] | null>(null);

  useEffect(() => {
    if (!student) return;
    authFetch<Notice[]>("/api/notices/?page_size=50")
      .then((all) =>
        setNotices(
          all.filter(
            (n) =>
              n.audience === "everyone" ||
              (n.audience === "class" && n.target_class_id === student.class_id),
          ),
        ),
      )
      .catch((e) => {
        toast(e instanceof Error ? e.message : "Failed to load notices", "error");
        setNotices([]);
      });
  }, [student, toast]);

  if (!student || !notices) return <Spinner />;

  return (
    <div className="space-y-3">
      {notices.length === 0 && <p className="text-sm text-slate-400 font-semibold">No notices yet.</p>}
      {notices.map((notice) => (
        <div key={notice.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-1.5">
          <div className="flex items-center gap-2">
            <p className="font-extrabold text-slate-800">{notice.title}</p>
            {notice.audience === "class" && (
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-lg text-[10px] font-bold uppercase">
                Your class
              </span>
            )}
            <span className="ml-auto text-xs text-slate-400 font-bold">{formatDate(notice.published_at)}</span>
          </div>
          <p className="text-sm text-slate-600 font-semibold leading-relaxed">{notice.content}</p>
          {notice.attachment_url && (
            <a
              href={notice.attachment_url}
              target="_blank"
              rel="noopener"
              className="text-indigo-600 text-sm font-bold hover:underline"
            >
              Download attachment
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

export default function StudentNotices() {
  return (
    <PortalShell portal="student" title="Notices">
      <NoticesView />
    </PortalShell>
  );
}

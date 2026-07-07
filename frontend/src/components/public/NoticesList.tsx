import { useEffect, useState } from "react";
import { publicGet } from "../../lib/api";

interface DisplayNotice {
  id: number;
  date: string;
  title: string;
  category: string;
  body: string;
  pdf: string | null;
}

interface ApiNotice {
  id: number;
  title: string;
  content: string;
  attachment_url: string | null;
  published_at: string | null;
}

// Shown until live notices load; kept if the backend is unreachable.
const fallbackNotices: DisplayNotice[] = [
  {
    id: -1,
    date: "June 15, 2026",
    title: "Reopening of School after Summer Vacation",
    category: "General",
    body: "Classes for Nursery to Class X will resume on Monday, July 1st, 2026. Uniforms and study materials can be collected from the school desk.",
    pdf: null,
  },
  {
    id: -2,
    date: "May 10, 2026",
    title: "Unit Test-I Exam Datesheet & Syllabus",
    category: "Examination",
    body: "The Unit Test-I examinations are scheduled to commence from July 20th, 2026. The detailed Datesheet and syllabus copies have been uploaded to respective student portals.",
    pdf: null,
  },
  {
    id: -3,
    date: "April 20, 2026",
    title: "Notice regarding Fee Installment Payment",
    category: "Fees",
    body: "This is a reminder that the First Term fee payment is due on or before June 30th, 2026. Payments can be completed online via the Student Portal or in cash at the school desk.",
    pdf: null,
  },
];

function inferCategory(title: string): string {
  const lower = title.toLowerCase();
  if (/(exam|test|datesheet|result)/.test(lower)) return "Examination";
  if (/(fee|payment|due)/.test(lower)) return "Fees";
  if (/(holiday|vacation)/.test(lower)) return "Holiday";
  return "General";
}

function toDisplay(notice: ApiNotice): DisplayNotice {
  return {
    id: notice.id,
    date: notice.published_at
      ? new Date(notice.published_at).toLocaleDateString("en-IN", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      : "",
    title: notice.title,
    category: inferCategory(notice.title),
    body: notice.content,
    pdf: notice.attachment_url,
  };
}

const categoryClass = (category: string) =>
  category === "Examination"
    ? "bg-rose-50 text-rose-700 border border-rose-100/50"
    : category === "Fees"
      ? "bg-amber-50 text-amber-700 border border-amber-100/50"
      : "bg-indigo-50 text-indigo-700 border border-indigo-100/50";

export default function NoticesList() {
  const [notices, setNotices] = useState<DisplayNotice[]>(fallbackNotices);

  useEffect(() => {
    publicGet<ApiNotice[]>("/api/public/notices?limit=50").then((live) => {
      if (live && live.length > 0) setNotices(live.map(toDisplay));
    });
  }, []);

  return (
    <>
      {notices.map((notice) => (
        <div
          key={notice.id}
          className="bg-white p-6 md:p-8 rounded-3xl border border-slate-100 shadow-sm flex flex-col md:flex-row gap-6 hover:shadow-md transition"
        >
          <div className="flex-shrink-0 md:w-36 text-slate-400 font-extrabold text-sm">
            {notice.date}
          </div>
          <div className="flex-1 space-y-4">
            <div className="space-y-2">
              <span
                className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider ${categoryClass(notice.category)}`}
              >
                {notice.category}
              </span>
              <h3 className="text-xl font-extrabold text-slate-800 leading-snug">{notice.title}</h3>
              <p className="text-sm text-slate-500 font-semibold leading-relaxed">{notice.body}</p>
            </div>
            {notice.pdf && (
              <div className="pt-2">
                <a
                  href={notice.pdf}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/50 rounded-xl text-xs font-bold transition shadow-sm"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Attachment
                </a>
              </div>
            )}
          </div>
        </div>
      ))}
    </>
  );
}

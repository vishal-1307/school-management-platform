import { useEffect, useState } from "react";
import { Award } from "lucide-react";
import { authFetch } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, Spinner, formatDate, useToast } from "../portal/kit";

interface PublishedExam {
  id: number;
  name: string;
  exam_type: string;
  start_date: string;
  student_id: number;
}

interface ReportCard {
  student_name: string;
  admission_number: string;
  class_name: string;
  exam_name: string;
  subjects: {
    subject_name: string;
    max_marks: number;
    passing_marks: number;
    marks_obtained: number | null;
    grade: string | null;
    passed: boolean;
  }[];
  total_marks: number;
  total_obtained: number;
  percentage: number;
  overall_grade: string;
  result: string;
}

function ResultsView() {
  const toast = useToast();
  const [exams, setExams] = useState<PublishedExam[] | null>(null);
  const [card, setCard] = useState<ReportCard | null>(null);
  const [loadingCard, setLoadingCard] = useState(false);

  useEffect(() => {
    authFetch<PublishedExam[]>("/api/exams/my-results")
      .then(setExams)
      .catch((e) => {
        toast(e instanceof Error ? e.message : "Failed to load results", "error");
        setExams([]);
      });
  }, [toast]);

  const openCard = async (exam: PublishedExam) => {
    setLoadingCard(true);
    try {
      setCard(await authFetch<ReportCard>(`/api/exams/${exam.id}/report-card/${exam.student_id}`));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load report card", "error");
    } finally {
      setLoadingCard(false);
    }
  };

  if (!exams) return <Spinner />;

  return (
    <>
      {exams.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm py-12 px-6 flex flex-col items-center gap-3 text-center">
          <span className="w-12 h-12 rounded-full bg-slate-50 text-slate-300 flex items-center justify-center">
            <Award className="w-6 h-6" />
          </span>
          <p className="text-sm font-bold text-slate-500">No results published yet</p>
          <p className="text-xs text-slate-400 font-semibold max-w-xs">
            They'll appear here as soon as the school releases them.
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        {exams.map((exam) => (
          <button
            key={exam.id}
            onClick={() => openCard(exam)}
            className="bg-white px-5 py-4 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition text-left"
          >
            <p className="font-extrabold text-slate-800">{exam.name}</p>
            <p className="text-xs text-slate-400 font-bold">{formatDate(exam.start_date)}</p>
          </button>
        ))}
      </div>

      {loadingCard && <Spinner />}

      {card && (
        <div id="report-card" className="bg-white rounded-2xl border-2 border-slate-200 p-8 max-w-2xl space-y-5 print:border-0">
          <div className="text-center space-y-1">
            <h2 className="font-heading font-extrabold text-xl text-slate-900">Report Card</h2>
            <p className="text-sm font-bold text-slate-600">{card.exam_name}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm font-semibold text-slate-600">
            <p>Name: <b className="text-slate-900">{card.student_name}</b></p>
            <p>Adm. No: <b className="text-slate-900">{card.admission_number}</b></p>
            <p>Class: <b className="text-slate-900">{card.class_name}</b></p>
            <p>
              Result:{" "}
              <b className={card.result === "Pass" ? "text-emerald-600" : "text-rose-600"}>
                {card.result}
              </b>
            </p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-bold uppercase text-slate-400 border-b border-slate-200">
                <th className="py-2">Subject</th>
                <th className="py-2 text-right">Max</th>
                <th className="py-2 text-right">Obtained</th>
                <th className="py-2 text-right">Grade</th>
              </tr>
            </thead>
            <tbody>
              {card.subjects.map((subject) => (
                <tr key={subject.subject_name} className="border-b border-slate-50 font-semibold">
                  <td className="py-2">{subject.subject_name}</td>
                  <td className="py-2 text-right">{subject.max_marks}</td>
                  <td className={`py-2 text-right ${subject.passed ? "" : "text-rose-600"}`}>
                    {subject.marks_obtained ?? "—"}
                  </td>
                  <td className="py-2 text-right">{subject.grade ?? "—"}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="font-extrabold text-slate-900">
                <td className="py-2">Total</td>
                <td className="py-2 text-right">{card.total_marks}</td>
                <td className="py-2 text-right">{card.total_obtained}</td>
                <td className="py-2 text-right">{card.overall_grade}</td>
              </tr>
            </tfoot>
          </table>
          <p className="text-center text-sm font-bold text-slate-600">
            Percentage: <span className="text-indigo-600">{card.percentage}%</span>
          </p>
          <div className="flex justify-end print:hidden">
            <Button variant="secondary" onClick={() => window.print()}>
              Print / Save PDF
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

export default function StudentResults() {
  return (
    <PortalShell portal="student" title="Results & Report Card">
      <ResultsView />
    </PortalShell>
  );
}

import { useState, useRef, useEffect } from "react";
import { publicGet } from "../lib/api";

interface Notice {
  id: number;
  text: string;
  isNew: boolean;
  date: string;
}

interface ApiNotice {
  id: number;
  title: string;
  published_at: string | null;
}

// Fallback shown until (and unless) live notices load from the backend.
const fallbackNotices: Notice[] = [
  { id: 1, text: "Admissions open for 2025–26 session — Limited seats available!", isNew: true, date: "Jun 15" },
  { id: 2, text: "Annual Day celebration on 28th July 2025 — All parents are invited", isNew: true, date: "Jun 12" },
  { id: 3, text: "Summer vacation: 15th May to 30th June 2025", isNew: false, date: "May 10" },
  { id: 4, text: "PTM for Classes I–V on 5th July 2025 at 10:00 AM", isNew: true, date: "Jun 18" },
  { id: 5, text: "Inter-school Science Exhibition — Register by 20th July", isNew: false, date: "Jun 8" },
  { id: 6, text: "New smart classrooms inaugurated — State-of-the-art learning!", isNew: false, date: "May 25" },
];

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000;

function toTickerNotice(notice: ApiNotice): Notice {
  const published = notice.published_at ? new Date(notice.published_at) : null;
  return {
    id: notice.id,
    text: notice.title,
    isNew: published !== null && Date.now() - published.getTime() < TWO_WEEKS_MS,
    date: published
      ? published.toLocaleDateString("en-IN", { month: "short", day: "numeric" })
      : "",
  };
}

export default function NoticeTicker() {
  const [isPaused, setIsPaused] = useState(false);
  const [notices, setNotices] = useState<Notice[]>(fallbackNotices);
  const tickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    publicGet<ApiNotice[]>("/api/public/notices?limit=10").then((live) => {
      if (live && live.length > 0) setNotices(live.map(toTickerNotice));
    });
  }, []);

  return (
    <div
      className="relative overflow-hidden bg-gradient-to-r from-primary-900 via-primary-800 to-primary-900 py-3"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Label */}
      <div className="absolute left-0 top-0 bottom-0 z-10 flex items-center px-4 bg-secondary-500 shadow-lg">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-white animate-pulse" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 3a1 1 0 00-1.447-.894L8.763 6H5a3 3 0 000 6h.28l1.771 5.316A1 1 0 008 18h1a1 1 0 001-1v-4.382l6.553 3.276A1 1 0 0018 15V3z" clipRule="evenodd"/>
          </svg>
          <span className="text-white font-heading font-semibold text-sm hidden sm:inline">NOTICES</span>
        </div>
      </div>

      {/* Scrolling Content */}
      <div className="ml-28 sm:ml-36">
        <div
          ref={tickerRef}
          className="flex gap-12 whitespace-nowrap"
          style={{
            animation: `ticker 40s linear infinite`,
            animationPlayState: isPaused ? "paused" : "running",
          }}
        >
          {/* Duplicate notices for seamless loop */}
          {[...notices, ...notices].map((notice, i) => (
            <div key={`${notice.id}-${i}`} className="inline-flex items-center gap-3 text-sm">
              {notice.isNew && (
                <span className="flex-shrink-0 px-2 py-0.5 bg-secondary-500 text-white text-[10px] font-bold rounded-full uppercase tracking-wider animate-pulse">
                  New
                </span>
              )}
              <span className="text-white/90 font-medium">{notice.text}</span>
              <span className="text-primary-300 text-xs">({notice.date})</span>
              <span className="text-primary-500">•</span>
            </div>
          ))}
        </div>
      </div>

      {/* Fade edges */}
      <div className="absolute left-28 sm:left-36 top-0 bottom-0 w-8 bg-gradient-to-r from-primary-900 to-transparent z-[5] pointer-events-none"></div>
      <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-primary-900 to-transparent z-[5] pointer-events-none"></div>
    </div>
  );
}

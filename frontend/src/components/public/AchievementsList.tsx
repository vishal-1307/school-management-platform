import { useEffect, useState } from "react";
import { publicGet } from "../../lib/api";

interface DisplayAchievement {
  id: number;
  name: string;
  award: string;
  desc: string;
  image: string;
}

interface ApiAchievement {
  id: number;
  title: string;
  description: string | null;
  image_url: string | null;
  date: string | null;
  category: string | null;
}

const PLACEHOLDER_IMAGE =
  "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?w=400&fit=crop";

// Shown until live achievements load; kept if the backend is unreachable.
const fallbackAchievements: DisplayAchievement[] = [
  {
    id: -1,
    name: "Master Aarav Sharma (Class X)",
    award: "State Science Talent Search Winner",
    desc: "Awarded first place for designing a low-cost water purification model using smart sensors.",
    image: "https://images.unsplash.com/photo-1544717305-2782549b5136?w=400&fit=crop",
  },
  {
    id: -2,
    name: "Miss Riya Verma (Class VIII)",
    award: "District Under-14 Chess Champion",
    desc: "Maintained a clean sweep of 7 rounds to win the gold medal in the inter-school chess championship.",
    image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&fit=crop",
  },
];

export default function AchievementsList() {
  const [achievements, setAchievements] = useState<DisplayAchievement[]>(fallbackAchievements);

  useEffect(() => {
    publicGet<ApiAchievement[]>("/api/cms/achievements").then((live) => {
      if (live && live.length > 0) {
        setAchievements(
          live.map((item) => ({
            id: item.id,
            name: item.title,
            award: item.category
              ? item.category.charAt(0).toUpperCase() + item.category.slice(1)
              : "Achievement",
            desc: item.description ?? "",
            image: item.image_url ?? PLACEHOLDER_IMAGE,
          })),
        );
      }
    });
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {achievements.map((ach) => (
        <div
          key={ach.id}
          className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm flex flex-col sm:flex-row gap-6 items-center hover:shadow-md transition"
        >
          <img
            src={ach.image}
            alt={ach.name}
            loading="lazy"
            className="w-24 h-24 sm:w-32 sm:h-32 rounded-2xl object-cover shadow border border-slate-100 flex-shrink-0"
          />
          <div className="space-y-2">
            <span className="px-2.5 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs font-bold uppercase tracking-wider">
              {ach.award}
            </span>
            <h3 className="font-extrabold text-slate-800 text-lg leading-tight">{ach.name}</h3>
            <p className="text-xs text-slate-500 font-semibold leading-relaxed">{ach.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

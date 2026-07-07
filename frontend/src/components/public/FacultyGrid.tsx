import { useEffect, useState } from "react";
import { publicGet } from "../../lib/api";

interface DisplayTeacher {
  name: string;
  subject: string;
  qualification: string;
  image: string;
}

interface Department {
  name: string;
  teachers: DisplayTeacher[];
}

interface ApiFaculty {
  id: number;
  first_name: string;
  last_name: string;
  photo_url: string | null;
  qualification: string | null;
  designation: string | null;
}

const PLACEHOLDER_PHOTO =
  "https://ui-avatars.com/api/?background=eef2ff&color=4f46e5&size=256&name=";

// Shown until live staff data loads; kept if the backend is unreachable.
const fallbackDepartments: Department[] = [
  {
    name: "Primary & Secondary Faculty",
    teachers: [
      {
        name: "Mrs. Sunita Kaul",
        subject: "Mathematics",
        qualification: "M.Sc. (Maths), B.Ed.",
        image: "https://images.unsplash.com/photo-1580894732444-8febeb78fb3e?w=300&fit=crop",
      },
      {
        name: "Mr. Ramesh Joshi",
        subject: "Science & Physics",
        qualification: "M.Sc. (Physics), B.Ed.",
        image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&fit=crop",
      },
      {
        name: "Mrs. Priya Sen",
        subject: "English Literature",
        qualification: "M.A. (English), B.Ed.",
        image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?w=300&fit=crop",
      },
      {
        name: "Mr. Amit Pathak",
        subject: "Social Sciences",
        qualification: "M.A. (History), B.Ed.",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&fit=crop",
      },
    ],
  },
  {
    name: "Kindergarten & Pre-Primary",
    teachers: [
      {
        name: "Mrs. Meera Das",
        subject: "Nursery Teacher",
        qualification: "N.T.T., Montessori Trained",
        image: "https://images.unsplash.com/photo-1554774853-aae0a22c8aa4?w=300&fit=crop",
      },
      {
        name: "Ms. Shalini Roy",
        subject: "LKG Coordinator",
        qualification: "B.A., Montessori Certified",
        image: "https://images.unsplash.com/photo-1594744803329-e58b31de215f?w=300&fit=crop",
      },
    ],
  },
];

export default function FacultyGrid() {
  const [departments, setDepartments] = useState<Department[]>(fallbackDepartments);

  useEffect(() => {
    publicGet<ApiFaculty[]>("/api/public/faculty").then((live) => {
      if (live && live.length > 0) {
        setDepartments([
          {
            name: "Our Teaching Team",
            teachers: live.map((staff) => {
              const name = `${staff.first_name} ${staff.last_name}`.trim();
              return {
                name,
                subject: staff.designation ?? "Faculty",
                qualification: staff.qualification ?? "",
                image: staff.photo_url ?? `${PLACEHOLDER_PHOTO}${encodeURIComponent(name)}`,
              };
            }),
          },
        ]);
      }
    });
  }, []);

  return (
    <>
      {departments.map((dept) => (
        <section key={dept.name} className="bg-slate-50 border-t border-slate-100 py-20">
          <div className="max-w-6xl mx-auto px-4 space-y-12">
            <div className="text-center max-w-2xl mx-auto space-y-4">
              <h2 className="text-3xl font-extrabold font-heading text-slate-900">{dept.name}</h2>
              <p className="text-slate-500 font-semibold">
                Highly trained subject specialists and early-learning experts.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {dept.teachers.map((teacher) => (
                <div
                  key={teacher.name}
                  className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm text-center hover:shadow-md transition duration-300 space-y-4"
                >
                  <img
                    src={teacher.image}
                    alt={teacher.name}
                    loading="lazy"
                    className="w-32 h-32 rounded-full object-cover mx-auto shadow border border-slate-100 aspect-square"
                  />
                  <div className="space-y-1">
                    <h3 className="font-bold text-slate-800 leading-tight">{teacher.name}</h3>
                    <p className="text-indigo-600 text-xs font-bold">{teacher.subject}</p>
                    <p className="text-xs text-slate-500 font-semibold leading-relaxed">
                      {teacher.qualification}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      ))}
    </>
  );
}

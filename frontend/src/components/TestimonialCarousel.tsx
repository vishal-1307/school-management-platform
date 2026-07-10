import { useState, useEffect, useCallback } from "react";

interface Testimonial {
  quote: string;
  name: string;
  relation: string;
  childClass: string;
}

const testimonials: Testimonial[] = [
  {
    quote: "Knowledge Academy has been a blessing for our family. The teachers go above and beyond to ensure every child feels valued and supported. My daughter's confidence has grown tremendously since she joined.",
    name: "Mrs. Sunita Sharma",
    relation: "Parent",
    childClass: "Class 5",
  },
  {
    quote: "The perfect balance of academics and extracurricular activities sets this school apart. My son has discovered his passion for science through the excellent lab facilities and dedicated faculty.",
    name: "Mr. Rajesh Kumar",
    relation: "Parent",
    childClass: "Class 8",
  },
  {
    quote: "We moved to this city specifically for this school. The CBSE curriculum is delivered with such care and innovation that our children actually look forward to going to school every morning.",
    name: "Mrs. Priya Mehta",
    relation: "Parent",
    childClass: "Class 3",
  },
  {
    quote: "From the warm reception at the gate to the thoughtful parent-teacher meetings, every interaction shows how much this institution cares. Our younger one is now enrolled too!",
    name: "Mr. Anil Verma",
    relation: "Parent",
    childClass: "Class 10",
  },
  {
    quote: "The school's focus on holistic development is genuine, not just a tagline. My daughter participates in dance, debate, and coding — all within the school day. Truly impressive.",
    name: "Mrs. Kavita Joshi",
    relation: "Parent",
    childClass: "Class 7",
  },
];

export default function TestimonialCarousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const goTo = useCallback(
    (index: number) => {
      if (isAnimating) return;
      setIsAnimating(true);
      setCurrentIndex(index);
      setTimeout(() => setIsAnimating(false), 500);
    },
    [isAnimating]
  );

  const next = useCallback(() => {
    goTo((currentIndex + 1) % testimonials.length);
  }, [currentIndex, goTo]);

  // Auto-rotate every 5 seconds
  useEffect(() => {
    const timer = setInterval(next, 5000);
    return () => clearInterval(timer);
  }, [next]);

  const current = testimonials[currentIndex];

  return (
    <div className="relative max-w-4xl mx-auto">
      {/* Quote Icon */}
      <div className="absolute -top-6 left-1/2 -translate-x-1/2 w-12 h-12 rounded-full bg-gradient-to-br from-primary-600 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-600/30 z-10">
        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zM0 21v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151C7.563 6.068 6 8.789 6 11h4v10H0z" />
        </svg>
      </div>

      {/* Testimonial Card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8 md:p-12 pt-12 text-center">
        <div
          key={currentIndex}
          className="animate-fade-in"
        >
          <p className="text-lg md:text-xl text-slate-600 leading-relaxed italic mb-8">
            &ldquo;{current.quote}&rdquo;
          </p>

          <div className="flex flex-col items-center">
            {/* Avatar placeholder */}
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center mb-3">
              <span className="text-xl font-heading font-bold text-primary-600">
                {current.name.charAt(0)}
              </span>
            </div>
            <h4 className="font-heading font-semibold text-slate-900 text-lg">
              {current.name}
            </h4>
            <p className="text-sm text-primary-600 font-medium">
              {current.relation} • {current.childClass}
            </p>
          </div>
        </div>

        {/* Navigation Dots */}
        <div className="flex items-center justify-center gap-2 mt-8">
          {testimonials.map((_, index) => (
            <button
              key={index}
              type="button"
              onClick={() => goTo(index)}
              aria-label={`Go to testimonial ${index + 1}`}
              aria-current={index === currentIndex}
              className="p-3 -m-1 flex items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
            >
              <span
                className={`block transition-all duration-300 rounded-full ${
                  index === currentIndex
                    ? "w-8 h-3 bg-primary-600"
                    : "w-3 h-3 bg-slate-200 hover:bg-primary-300"
                }`}
              />
            </button>
          ))}
        </div>
      </div>

      {/* Arrow Buttons (Desktop) */}
      <button
        onClick={() => goTo((currentIndex - 1 + testimonials.length) % testimonials.length)}
        className="hidden md:flex absolute left-0 top-1/2 -translate-y-1/2 -translate-x-14 w-10 h-10 rounded-full bg-white shadow-lg border border-slate-100 items-center justify-center text-slate-400 hover:text-primary-600 hover:border-primary-200 transition-all"
        aria-label="Previous testimonial"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <button
        onClick={() => next()}
        className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 translate-x-14 w-10 h-10 rounded-full bg-white shadow-lg border border-slate-100 items-center justify-center text-slate-400 hover:text-primary-600 hover:border-primary-200 transition-all"
        aria-label="Next testimonial"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}

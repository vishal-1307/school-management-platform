import { useState } from "react";
import { publicPost } from "../lib/api";

interface FormData {
  name: string;
  phone: string;
  email: string;
  message: string;
}

const initialFormData: FormData = { name: "", phone: "", email: "", message: "" };

const inputClass =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-indigo-600 focus:border-indigo-600 transition";

export default function ContactForm() {
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("submitting");
    try {
      await publicPost("/api/public/contact", {
        name: formData.name,
        phone: formData.phone || null,
        email: formData.email || null,
        message: formData.message,
      });
      setStatus("success");
      setFormData(initialFormData);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong");
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div className="text-center py-12 space-y-4">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="font-heading font-bold text-xl text-slate-900">Message Sent!</h3>
        <p className="text-sm text-slate-500 font-semibold">
          The school office will get back to you within 1–2 working days.
        </p>
        <button
          onClick={() => setStatus("idle")}
          className="text-indigo-600 font-bold text-sm hover:underline"
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <form className="space-y-4 font-semibold text-sm" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-slate-600">Full Name</label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => handleChange("name", e.target.value)}
            className={inputClass}
            placeholder="e.g. John Doe"
          />
        </div>
        <div className="space-y-2">
          <label className="text-slate-600">Phone Number</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => handleChange("phone", e.target.value)}
            className={inputClass}
            placeholder="e.g. +91 98765 43210"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-slate-600">Email Address</label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => handleChange("email", e.target.value)}
          className={inputClass}
          placeholder="e.g. john@example.com"
        />
      </div>

      <div className="space-y-2">
        <label className="text-slate-600">Message</label>
        <textarea
          required
          rows={5}
          value={formData.message}
          onChange={(e) => handleChange("message", e.target.value)}
          className={`${inputClass} resize-none`}
          placeholder="Write your message here..."
        />
      </div>

      {status === "error" && (
        <p className="text-red-600 text-sm font-semibold bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          Could not send your message ({errorMessage}). Please try again, or call the office directly.
        </p>
      )}

      <button
        type="submit"
        disabled={status === "submitting"}
        className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-bold rounded-xl transition duration-300 shadow-md hover:shadow-indigo-600/10"
      >
        {status === "submitting" ? "Sending…" : "Send Message"}
      </button>
    </form>
  );
}

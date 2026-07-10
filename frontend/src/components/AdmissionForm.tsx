import { useState } from "react";
import { publicPost } from "../lib/api";

interface FormData {
  childName: string;
  dateOfBirth: string;
  classApplying: string;
  parentName: string;
  phone: string;
  email: string;
  address: string;
  source: string;
  message: string;
}

const initialFormData: FormData = {
  childName: "",
  dateOfBirth: "",
  classApplying: "",
  parentName: "",
  phone: "",
  email: "",
  address: "",
  source: "",
  message: "",
};

const classOptions = [
  "Pre-Nursery",
  "Nursery",
  "LKG",
  "UKG",
  "Class I",
  "Class II",
  "Class III",
  "Class IV",
  "Class V",
  "Class VI",
  "Class VII",
  "Class VIII",
  "Class IX",
  "Class X",
  "Class XI (Science)",
  "Class XI (Commerce)",
  "Class XII (Science)",
  "Class XII (Commerce)",
];

const sourceOptions = [
  "Friend / Relative",
  "Social Media",
  "Google Search",
  "Newspaper Advertisement",
  "School Website",
  "Walk-in Visit",
  "Other",
];

export default function AdmissionForm() {
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    if (!formData.childName.trim()) newErrors.childName = "Child's name is required";
    if (!formData.dateOfBirth) newErrors.dateOfBirth = "Date of birth is required";
    if (!formData.classApplying) newErrors.classApplying = "Please select a class";
    if (!formData.parentName.trim()) newErrors.parentName = "Parent/Guardian name is required";
    if (!formData.phone.trim()) {
      newErrors.phone = "Phone number is required";
    } else if (!/^[6-9]\d{9}$/.test(formData.phone.replace(/\s/g, ""))) {
      newErrors.phone = "Please enter a valid 10-digit mobile number";
    }
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }
    if (!formData.address.trim()) newErrors.address = "Address is required";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setStatus("submitting");

    try {
      await publicPost("/api/admissions/enquiry", {
        child_name: formData.childName,
        dob: formData.dateOfBirth || null,
        class_applying: formData.classApplying,
        parent_name: formData.parentName,
        phone: formData.phone.replace(/\s/g, ""),
        email: formData.email || null,
        address: formData.address || null,
        source: formData.source || null,
        message: formData.message || null,
      });
      setStatus("success");
      setFormData(initialFormData);
    } catch {
      setStatus("error");
    }
  };

  const handleChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  if (status === "success") {
    return (
      <div className="text-center py-16 px-8">
        <div className="w-20 h-20 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-6 animate-scale-in">
          <svg className="w-10 h-10 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="font-heading font-bold text-2xl text-slate-900 mb-3">Thank You!</h3>
        <p className="text-slate-600 mb-2">Your admission enquiry has been submitted successfully.</p>
        <p className="text-sm text-slate-500 mb-8">Our admissions team will contact you within 24–48 hours.</p>
        <button
          onClick={() => setStatus("idle")}
          className="px-6 py-3 bg-primary-600 text-white font-semibold rounded-xl hover:bg-primary-700 transition-colors"
        >
          Submit Another Enquiry
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {status === "error" && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
          </svg>
          Something went wrong. Please try again.
        </div>
      )}

      {/* Child Information */}
      <div>
        <h4 className="font-heading font-semibold text-slate-900 text-lg mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center text-sm font-bold">1</span>
          Child&apos;s Information
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InputField
            label="Child's Full Name"
            value={formData.childName}
            onChange={(v) => handleChange("childName", v)}
            error={errors.childName}
            placeholder="Enter child's full name"
            required
          />
          <InputField
            label="Date of Birth"
            type="date"
            value={formData.dateOfBirth}
            onChange={(v) => handleChange("dateOfBirth", v)}
            error={errors.dateOfBirth}
            required
          />
          <SelectField
            label="Class Applying For"
            value={formData.classApplying}
            onChange={(v) => handleChange("classApplying", v)}
            options={classOptions}
            error={errors.classApplying}
            placeholder="Select class"
            required
          />
        </div>
      </div>

      {/* Parent Information */}
      <div>
        <h4 className="font-heading font-semibold text-slate-900 text-lg mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center text-sm font-bold">2</span>
          Parent / Guardian Details
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InputField
            label="Parent/Guardian Name"
            value={formData.parentName}
            onChange={(v) => handleChange("parentName", v)}
            error={errors.parentName}
            placeholder="Enter parent/guardian name"
            required
          />
          <InputField
            label="Mobile Number"
            type="tel"
            value={formData.phone}
            onChange={(v) => handleChange("phone", v)}
            error={errors.phone}
            placeholder="10-digit mobile number"
            required
          />
          <InputField
            label="Email Address"
            type="email"
            value={formData.email}
            onChange={(v) => handleChange("email", v)}
            error={errors.email}
            placeholder="your@email.com (optional)"
          />
          <SelectField
            label="How did you hear about us?"
            value={formData.source}
            onChange={(v) => handleChange("source", v)}
            options={sourceOptions}
            placeholder="Select source"
          />
        </div>
      </div>

      {/* Address & Message */}
      <div>
        <h4 className="font-heading font-semibold text-slate-900 text-lg mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center text-sm font-bold">3</span>
          Additional Details
        </h4>
        <div className="space-y-4">
          <TextareaField
            label="Residential Address"
            value={formData.address}
            onChange={(v) => handleChange("address", v)}
            error={errors.address}
            placeholder="Enter complete residential address"
            rows={2}
            required
          />
          <TextareaField
            label="Additional Message"
            value={formData.message}
            onChange={(v) => handleChange("message", v)}
            placeholder="Any specific query or requirement? (optional)"
            rows={3}
          />
        </div>
      </div>

      {/* Submit */}
      <div className="pt-4">
        <button
          type="submit"
          disabled={status === "submitting"}
          className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-heading font-semibold text-lg rounded-xl hover:from-primary-700 hover:to-primary-800 shadow-lg shadow-primary-600/30 hover:shadow-primary-600/50 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
        >
          {status === "submitting" ? (
            <>
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Submitting...
            </>
          ) : (
            <>
              Submit Enquiry
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </>
          )}
        </button>
      </div>
    </form>
  );
}

/* ===== Reusable Field Components ===== */

function InputField({
  label,
  type = "text",
  value,
  onChange,
  error,
  placeholder,
  required,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full px-4 py-3 rounded-xl border text-base sm:text-sm transition-all duration-200 bg-white
          ${error
            ? "border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-200"
            : "border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200"
          }
          hover:border-slate-300 outline-none placeholder:text-slate-400`}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  error,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  error?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full px-4 py-3 rounded-xl border text-base sm:text-sm transition-all duration-200 bg-white appearance-none
          ${error
            ? "border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-200"
            : "border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200"
          }
          hover:border-slate-300 outline-none ${!value ? "text-slate-400" : "text-slate-900"}`}
      >
        <option value="">{placeholder || "Select..."}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

function TextareaField({
  label,
  value,
  onChange,
  error,
  placeholder,
  rows = 3,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
  rows?: number;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={`w-full px-4 py-3 rounded-xl border text-base sm:text-sm transition-all duration-200 bg-white resize-none
          ${error
            ? "border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-200"
            : "border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200"
          }
          hover:border-slate-300 outline-none placeholder:text-slate-400`}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

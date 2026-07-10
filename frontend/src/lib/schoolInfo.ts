/**
 * School contact/profile info for static public pages (footer, contact
 * page). Fetched once at BUILD time (these pages are prerendered — see
 * astro.config.mjs `output: "static"`), with the previous hardcoded
 * copy kept as a fallback so a slow/asleep backend during a Vercel build
 * never fails the build or leaves the footer blank.
 */

export interface SchoolInfo {
  name: string;
  address: string;
  contactEmail: string;
  contactPhone: string;
}

const FALLBACK: SchoolInfo = {
  name: "Knowledge Development Kindergarten Academy",
  address: "Sector 5, Knowledge Campus, Near City Park, New Delhi, 110001",
  contactEmail: "info@knowledgeacademy.edu.in",
  contactPhone: "+91 98765 43210",
};

const API_URL: string = (
  (import.meta.env.PUBLIC_API_URL as string | undefined) ?? "http://localhost:8000"
).replace(/\/+$/, "");

export async function getSchoolInfo(): Promise<SchoolInfo> {
  try {
    const response = await fetch(`${API_URL}/api/public/school`, {
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) return FALLBACK;
    const data = await response.json();
    if (!data) return FALLBACK;
    return {
      name: data.name || FALLBACK.name,
      address: data.address || FALLBACK.address,
      contactEmail: data.contact_email || FALLBACK.contactEmail,
      contactPhone: data.contact_phone || FALLBACK.contactPhone,
    };
  } catch {
    return FALLBACK;
  }
}

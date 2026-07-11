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
  /** Second number from the school's own signboard — display-only, no tel: link math. */
  contactPhoneAlt: string;
  /** Static facts verified against the school's own signage/social presence —
   * not yet wired to an admin-editable field (rarely change). */
  establishedYear: number;
  facebookUrl: string;
  mapsQuery: string;
}

const FALLBACK: SchoolInfo = {
  name: "Knowledge Development Kindergarten Academy",
  address: "Basopatti Road, Near Ugna Chawk, Benipatti, Madhubani, Bihar 847223",
  // TODO(placeholder — unverified): no official email was found on the
  // school's Google Maps listing, Facebook page, or directory listings.
  // Replace once the school confirms a real address.
  contactEmail: "info@knowledgeacademy.edu.in",
  contactPhone: "+91 99349 75151",
  contactPhoneAlt: "+91 99731 04141",
  establishedYear: 2005,
  facebookUrl: "https://www.facebook.com/kdkabenipatti/",
  mapsQuery: "Knowledge+Development+Kindergarten+Academy+Benipatti",
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
      ...FALLBACK,
      name: data.name || FALLBACK.name,
      address: data.address || FALLBACK.address,
      contactEmail: data.contact_email || FALLBACK.contactEmail,
      contactPhone: data.contact_phone || FALLBACK.contactPhone,
    };
  } catch {
    return FALLBACK;
  }
}

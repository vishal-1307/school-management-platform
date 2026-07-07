/**
 * Loads the signed-in teacher's staff record (with teaching assignments)
 * once and derives the class/section/subject combinations they may act on.
 */

import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";

export interface TeacherAssignment {
  id: number;
  subject_id: number;
  class_id: number;
  section_id: number;
}

export interface TeacherRecord {
  id: number;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  photo_url: string | null;
  qualification: string | null;
  designation: string | null;
  subject_assignments: TeacherAssignment[];
}

export function useTeacherRecord() {
  const [staff, setStaff] = useState<TeacherRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<TeacherRecord>("/api/staff/me")
      .then(setStaff)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load your record"));
  }, []);

  return { staff, error };
}

/** Unique class+section pairs the teacher is assigned to. */
export function classSections(staff: TeacherRecord | null): { class_id: number; section_id: number }[] {
  if (!staff) return [];
  const seen = new Set<string>();
  const pairs: { class_id: number; section_id: number }[] = [];
  for (const a of staff.subject_assignments) {
    const key = `${a.class_id}-${a.section_id}`;
    if (!seen.has(key)) {
      seen.add(key);
      pairs.push({ class_id: a.class_id, section_id: a.section_id });
    }
  }
  return pairs;
}

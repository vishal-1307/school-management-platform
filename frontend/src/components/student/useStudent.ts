/** Loads the signed-in student's own record once. */

import { useEffect, useState } from "react";
import { authFetch } from "../../lib/api";

export interface StudentRecord {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  dob: string;
  gender: string;
  photo_url: string | null;
  class_id: number;
  section_id: number;
  roll_number: number | null;
  address: string | null;
  parents: { name: string; phone: string; relation: string }[];
}

export function useStudentRecord() {
  const [student, setStudent] = useState<StudentRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<StudentRecord>("/api/students/me")
      .then(setStudent)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load your record"));
  }, []);

  return { student, error };
}

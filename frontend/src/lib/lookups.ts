/**
 * Cached reference data (classes, sections, subjects, academic years) used
 * by portal forms and tables everywhere.
 */

import { authFetch } from "./api";

export interface ClassInfo {
  id: number;
  name: string;
  numeric_order: number;
}

export interface SectionInfo {
  id: number;
  name: string;
  class_id: number;
  class_teacher_id: number | null;
}

export interface SubjectInfo {
  id: number;
  name: string;
  code: string;
}

export interface AcademicYearInfo {
  id: number;
  label: string;
  is_current: boolean;
}

export interface Lookups {
  classes: ClassInfo[];
  sections: SectionInfo[];
  subjects: SubjectInfo[];
  years: AcademicYearInfo[];
}

let cache: Lookups | null = null;

export async function getLookups(force = false): Promise<Lookups> {
  if (cache && !force) return cache;
  const [classes, sections, subjects, years] = await Promise.all([
    authFetch<ClassInfo[]>("/api/settings/classes"),
    authFetch<SectionInfo[]>("/api/settings/sections"),
    authFetch<SubjectInfo[]>("/api/settings/subjects"),
    authFetch<AcademicYearInfo[]>("/api/settings/academic-years").catch(() => []),
  ]);
  classes.sort((a, b) => a.numeric_order - b.numeric_order);
  cache = { classes, sections, subjects, years };
  return cache;
}

export function classNameOf(lookups: Lookups, classId: number | null): string {
  return lookups.classes.find((c) => c.id === classId)?.name ?? "—";
}

export function sectionNameOf(lookups: Lookups, sectionId: number | null): string {
  return lookups.sections.find((s) => s.id === sectionId)?.name ?? "—";
}

export function subjectNameOf(lookups: Lookups, subjectId: number | null): string {
  return lookups.subjects.find((s) => s.id === subjectId)?.name ?? "—";
}

export function sectionsForClass(lookups: Lookups, classId: number | ""): SectionInfo[] {
  if (classId === "") return [];
  return lookups.sections.filter((s) => s.class_id === classId);
}

export function currentYearOf(lookups: Lookups): AcademicYearInfo | undefined {
  return lookups.years.find((y) => y.is_current) ?? lookups.years[0];
}

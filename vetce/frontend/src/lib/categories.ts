/**
 * Dental subject categories. Mirrors src/vetce/pipeline/tagger.py on the backend.
 * Keep slugs and display names in sync.
 *
 * "non_dental" is excluded from this list because it's hidden by default
 * and shouldn't appear in user-facing filters.
 */

export type CategorySlug =
  | "periodontics"
  | "endodontics"
  | "oral_surgery"
  | "prosthodontics_restorative"
  | "orthodontics"
  | "oral_pathology"
  | "anesthesia_pain"
  | "imaging_radiology"
  | "dental_equipment"
  | "patient_handling_workflow"
  | "exotic_specialty_dentistry"
  | "general_dentistry";

export const CATEGORY_LABELS: Record<CategorySlug, string> = {
  periodontics: "Periodontics",
  endodontics: "Endodontics",
  oral_surgery: "Oral Surgery",
  prosthodontics_restorative: "Prosthodontics & Restorative",
  orthodontics: "Orthodontics",
  oral_pathology: "Oral Pathology",
  anesthesia_pain: "Anesthesia & Pain",
  imaging_radiology: "Imaging & Radiology",
  dental_equipment: "Dental Equipment",
  patient_handling_workflow: "Patient Workflow",
  exotic_specialty_dentistry: "Exotic Dentistry",
  general_dentistry: "General Dentistry",
};

/**
 * Categories in display order for filter UIs.
 * Listed roughly from most-common dental specialty to least.
 */
export const CATEGORY_OPTIONS: { value: CategorySlug; label: string }[] = (
  Object.entries(CATEGORY_LABELS) as [CategorySlug, string][]
).map(([value, label]) => ({ value, label }));

/**
 * Look up a label for a slug. Returns the slug itself if unrecognized
 * (defensive — handles new categories the frontend doesn't know about yet).
 */
export function categoryLabel(slug: string | null): string {
  if (!slug) return "";
  return CATEGORY_LABELS[slug as CategorySlug] ?? slug;
}
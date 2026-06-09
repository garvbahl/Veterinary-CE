/**
 * Colored pill for scrape-run status.
 *
 * Maps backend statuses to brand-consistent tones:
 *   success  → green
 *   partial  → amber
 *   failed   → red
 *   running  → blue
 *   <other>  → neutral gray
 */
type Props = {
  status: string | null | undefined;
};

const STATUS_STYLES: Record<string, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  failed: "bg-red-50 text-red-700 ring-1 ring-red-200",
  running: "bg-sky-50 text-sky-700 ring-1 ring-sky-200",
};

export function RunStatusBadge({ status }: Props) {
  if (!status) {
    return (
      <span className="inline-flex items-center rounded-pill bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
        no runs yet
      </span>
    );
  }

  const cls = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700 ring-1 ring-slate-200";

  return (
    <span className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
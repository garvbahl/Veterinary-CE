import type { Listing } from "@/lib/types";

/**
 * Single listing card for the browse page grid.
 *
 * Designed to be scannable in ~1 second: provider → dates → title → metadata.
 * Clicking anywhere opens the detail page (Step 6.6).
 */

function formatDateRange(starts: string | null, ends: string | null): string | null {
  if (!starts) return null;

  const startDate = new Date(starts);
  const startStr = startDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  if (!ends || ends === starts) {
    return startStr;
  }

  const endDate = new Date(ends);
  const endStr = endDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return `${startStr} – ${endStr}`;
}

function formatLabel(value: string | null): string {
  if (!value) return "";
  // Convert "on_demand" → "On Demand", "vets and techs" → "Vets and Techs"
  return value
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function ListingCard({ listing }: { listing: Listing }) {
  const dateLabel = formatDateRange(listing.starts_at, listing.ends_at);
  const cleanedDescription = (listing.description ?? "").replace(/\s+/g, " ").trim();

  return (
    <article className="group rounded-2xl border border-ink-100 bg-white p-6 shadow-card hover:shadow-cardHover hover:border-brand-200 transition-all">
      {/* Provider + date row */}
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-brand-600 uppercase tracking-wide">
          {listing.provider}
        </span>
        {dateLabel && (
          <span className="text-ink-400 font-medium">
            {dateLabel}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="mt-3 text-lg font-bold text-ink-900 leading-snug line-clamp-2 group-hover:text-brand-700 transition-colors">
        {listing.title}
      </h3>

      {/* Description (truncated to ~2 lines via line-clamp) */}
      {cleanedDescription && (
        <p className="mt-3 text-sm text-ink-600 leading-relaxed line-clamp-2">
          {cleanedDescription}
        </p>
      )}

      {/* Metadata badges */}
      <div className="mt-4 flex flex-wrap gap-2">
        {listing.credit_hours != null && (
          <Badge label={`${listing.credit_hours} CE credit${listing.credit_hours === 1 ? "" : "s"}`} tone="brand" />
        )}
        {listing.race_approved && (
          <Badge label="RACE-Approved" tone="success" />
        )}
        {listing.format && (
          <Badge label={formatLabel(listing.format)} tone="neutral" />
        )}
        {listing.audience && (
          <Badge label={formatLabel(listing.audience)} tone="neutral" />
        )}
        {listing.cost && (
          <Badge label={listing.cost} tone="neutral" />
        )}
      </div>

      {/* CTA */}
      <div className="mt-6 flex items-center justify-between gap-3">
        <a href={`/listings/${listing.id}`} className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors">
          View details →
        </a>
        {listing.registration_url && (
          <a href={listing.registration_url} target="_blank" rel="noopener noreferrer" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 text-sm font-semibold transition-colors">
            Register
          </a>
        )}
      </div>
    </article>
  );
}

// ===== Badge subcomponent =====
type BadgeTone = "brand" | "neutral" | "success";

function Badge({ label, tone }: { label: string; tone: BadgeTone }) {
  const styles: Record<BadgeTone, string> = {
    brand: "bg-brand-50 text-brand-700 border-brand-200",
    neutral: "bg-ink-50 text-ink-600 border-ink-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[tone]}`}
    >
      {label}
    </span>
  );
}
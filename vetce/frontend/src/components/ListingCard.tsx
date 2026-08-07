import type { Listing } from "@/lib/types";
import { categoryLabel } from "@/lib/categories";
import { speakerImage } from "@/lib/speakerImages";
import SpeakerAvatar from "./SpeakerAvatar";

/**
 * Single listing card for the browse page grid.
 *
 * PerioVive's own listings get a distinct "pop" treatment: a brand-tinted
 * background, a "From PerioVive" badge, a speaker headshot (when available),
 * and the brand left-border accent.
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

  return `${startStr} - ${endStr}`;
}

function formatLabel(value: string | null): string {
  if (!value) return "";
  return value
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function ListingCard({ listing }: { listing: Listing }) {
  const isPeriovive = listing.provider.trim().toLowerCase() === "periovive";
  // Featured = manually pinned for preferred placement. PerioVive's own cards
  // already have a distinct brand treatment, so the gold featured accent only
  // applies to non-PerioVive listings to avoid two competing accents.
  const isFeatured = listing.featured && !isPeriovive;
  const providerLabel = isPeriovive ? "PerioVive" : listing.provider;
  const dateLabel = formatDateRange(listing.starts_at, listing.ends_at);
  const cleanedDescription = (listing.description ?? "").replace(/\s+/g, " ").trim();
  const photo = isPeriovive
    ? (listing.presenter_image_url ?? speakerImage(listing.presenter))
    : null;

  return (
    <article
      className={`group rounded-2xl border p-6 shadow-card hover:shadow-cardHover transition-all ${
        isPeriovive
          ? "bg-brand-50/40 border-ink-100 border-l-4 border-l-brand-500 hover:border-brand-200"
          : isFeatured
          ? "bg-accent-gold/5 border-accent-gold/40 border-l-4 border-l-accent-gold hover:border-accent-gold/60"
          : "bg-white border-ink-100 hover:border-brand-200"
      }`}
    >
      {/* Featured badge (non-PerioVive pinned listings) */}
      {isFeatured && (
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-accent-gold text-white px-2.5 py-1 text-xs font-bold tracking-wide">
            <StarIcon />
            Featured
          </span>
        </div>
      )}

      {/* PerioVive badge */}
      {isPeriovive && (
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-brand-500 text-white px-2.5 py-1 text-xs font-bold tracking-wide">
            From PerioVive
          </span>
        </div>
      )}

      {/* Speaker avatar + presenter (PerioVive only, when we have a presenter) */}
      {isPeriovive && listing.presenter && (
        <div className="mb-4 flex items-center gap-3">
          <SpeakerAvatar src={photo} name={listing.presenter} />
          <span className="text-sm font-semibold text-ink-700">
            {listing.presenter}
          </span>
        </div>
      )}

      {/* Provider + date row */}
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-brand-600 uppercase tracking-wide">
          {providerLabel}
        </span>
        {dateLabel ? (
          <span className="text-ink-400 font-medium">{dateLabel}</span>
        ) : listing.format === "on_demand" ? (
          <span className="text-ink-400 font-medium">On-Demand</span>
        ) : null}
      </div>

      {/* Title */}
      <h3 className="mt-3 text-lg font-bold text-ink-900 leading-snug line-clamp-2 group-hover:text-brand-700 transition-colors">
        {listing.title}
      </h3>

      {/* Description */}
      {cleanedDescription && (
        <p className="mt-3 text-sm text-ink-600 leading-relaxed line-clamp-2">
          {cleanedDescription}
        </p>
      )}

      {/* Metadata badges */}
      <div className="mt-4 flex flex-wrap gap-2">
        {listing.subject_category && (
          <Badge label={categoryLabel(listing.subject_category)} tone="brand" />
        )}
        {listing.credit_hours != null && (
          <Badge label={`${listing.credit_hours} CE credit${listing.credit_hours === 1 ? "" : "s"}`} tone="brand" />
        )}
        {listing.race_approved && <Badge label="RACE-Approved" tone="success" />}
        {listing.format && <Badge label={formatLabel(listing.format)} tone="neutral" />}
        {listing.audience && <Badge label={formatLabel(listing.audience)} tone="neutral" />}
        {listing.cost && <Badge label={listing.cost} tone="neutral" />}
      </div>

      {/* CTA */}
      <div className="mt-6 flex items-center justify-between gap-3">
        <a href={`/listings/${listing.id}`} className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors">
          View details →
        </a>
        {listing.registration_url ? (
          <a href={listing.registration_url} target="_blank" rel="noopener noreferrer" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 text-sm font-semibold transition-colors">
            Register
          </a>
        ) : isPeriovive && listing.format === "live" ? (
          <span className="rounded-pill bg-ink-100 text-ink-500 px-4 py-2 text-sm font-semibold">
            Registration closed
          </span>
        ) : null}
      </div>
    </article>
  );
}

type BadgeTone = "brand" | "neutral" | "success";

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3" aria-hidden="true">
      <path d="M12 2l2.9 6.26L21.5 9.3l-4.75 4.64 1.12 6.56L12 17.4l-5.87 3.1 1.12-6.56L2.5 9.3l6.6-1.04L12 2z" />
    </svg>
  );
}

function Badge({ label, tone }: { label: string; tone: BadgeTone }) {
  const styles: Record<BadgeTone, string> = {
    brand: "bg-brand-50 text-brand-700 border-brand-200",
    neutral: "bg-ink-50 text-ink-600 border-ink-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[tone]}`}>
      {label}
    </span>
  );
}
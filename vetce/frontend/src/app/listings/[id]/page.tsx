import { fetchListing } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { notFound } from "next/navigation";
import Link from "next/link";

type PageProps = {
  params: Promise<{ id: string }>;
};

// Generate the browser tab title and SEO meta from the listing itself.
export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  const numericId = Number(id);
  if (Number.isNaN(numericId)) {
    return { title: "Listing — PerioVive CE" };
  }
  try {
    const listing = await fetchListing(numericId);
    return {
      title: `${listing.title} — PerioVive CE`,
      description: listing.description?.slice(0, 160) ?? undefined,
    };
  } catch {
    return { title: "Listing not found — PerioVive CE" };
  }
}

function formatDateRange(starts: string | null, ends: string | null): string | null {
  if (!starts) return null;
  const startDate = new Date(starts);
  const startStr = startDate.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  if (!ends || ends === starts) return startStr;
  const endDate = new Date(ends);
  const endStr = endDate.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  return `${startStr} – ${endStr}`;
}

function formatLabel(value: string | null): string {
  if (!value) return "";
  return value
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default async function ListingDetailPage({ params }: PageProps) {
  const { id } = await params;
  const numericId = Number(id);
  if (Number.isNaN(numericId)) {
    notFound();
  }

  let listing;
  try {
    listing = await fetchListing(numericId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    throw e;
  }

  const dateLabel = formatDateRange(listing.starts_at, listing.ends_at);
  const cleanedDescription = (listing.description ?? "").replace(/\s+/g, " ").trim();

  // Field rows we'll render in the metadata table.
  const metadataRows: Array<{ label: string; value: string }> = [];
  if (listing.credit_hours != null) {
    metadataRows.push({
      label: "CE Credits",
      value: `${listing.credit_hours} hour${listing.credit_hours === 1 ? "" : "s"}`,
    });
  }
  if (listing.race_approved !== null && listing.race_approved !== undefined) {
    metadataRows.push({
      label: "RACE Approved",
      value: listing.race_approved ? "Yes" : "No",
    });
  }
  if (listing.race_program_number) {
    metadataRows.push({ label: "RACE Program Number", value: listing.race_program_number });
  }
  if (listing.format) {
    metadataRows.push({ label: "Format", value: formatLabel(listing.format) });
  }
  if (listing.audience) {
    metadataRows.push({ label: "Audience", value: formatLabel(listing.audience) });
  }
  if (listing.delivery_method) {
    metadataRows.push({ label: "Delivery Method", value: listing.delivery_method });
  }
  if (listing.subject_category) {
    metadataRows.push({ label: "Subject", value: listing.subject_category });
  }
  if (listing.presenter) {
    metadataRows.push({ label: "Presenter", value: listing.presenter });
  }
  if (listing.cost) {
    metadataRows.push({ label: "Cost", value: listing.cost });
  }

  return (
    <main className="bg-ink-50/40 min-h-screen">
      <article className="max-w-4xl mx-auto px-6 py-12">
        {/* Breadcrumb */}
        <nav className="text-sm text-ink-400 mb-6">
          <Link href="/listings" className="hover:text-ink-900 transition-colors">
            ← Back to listings
          </Link>
        </nav>

        {/* Header card */}
        <header className="bg-white rounded-2xl border border-ink-100 shadow-card p-8 md:p-10">
          <p className="text-brand-600 font-semibold uppercase tracking-wide text-sm">
            {listing.provider}
          </p>
          <h1 className="mt-3 text-3xl md:text-4xl font-extrabold text-ink-900 leading-tight">
            {listing.title}
          </h1>

          {dateLabel && (
            <p className="mt-4 text-lg text-ink-600 font-medium">
              📅 {dateLabel}
            </p>
          )}

          {/* CTA buttons */}
          <div className="mt-8 flex flex-wrap gap-3">
            {listing.registration_url && (
              <a href={listing.registration_url} target="_blank" rel="noopener noreferrer" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-8 py-3 font-semibold transition-colors">
                Register →
              </a>
            )}
            <a href={listing.source_url} target="_blank" rel="noopener noreferrer" className="rounded-pill border border-ink-200 hover:border-ink-400 text-ink-900 px-8 py-3 font-semibold transition-colors">
              View on provider site
            </a>
          </div>
        </header>

        {/* Description */}
        {cleanedDescription && (
          <section className="mt-8 bg-white rounded-2xl border border-ink-100 shadow-card p-8 md:p-10">
            <h2 className="text-xl font-bold text-ink-900 mb-4">About this course</h2>
            <p className="text-ink-600 leading-relaxed whitespace-pre-wrap">
              {cleanedDescription}
            </p>
          </section>
        )}

        {/* Metadata table */}
        {metadataRows.length > 0 && (
          <section className="mt-8 bg-white rounded-2xl border border-ink-100 shadow-card p-8 md:p-10">
            <h2 className="text-xl font-bold text-ink-900 mb-6">Details</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
              {metadataRows.map((row) => (
                <div key={row.label} className="flex flex-col">
                  <dt className="text-xs font-semibold text-ink-400 uppercase tracking-wide">
                    {row.label}
                  </dt>
                  <dd className="mt-1 text-ink-900 font-medium">{row.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        {/* Source attribution */}
        <p className="mt-8 text-xs text-ink-400 text-center">
          Listing aggregated from {listing.provider}. Always confirm details on the
          provider's site before registering.
        </p>
      </article>
    </main>
  );
}
import { fetchListings } from "@/lib/api";
import ListingCard from "@/components/ListingCard";
import Link from "next/link";

export default async function Home() {
  // Fetch upcoming dental listings to feature.
  let featured: Awaited<ReturnType<typeof fetchListings>>["items"] = [];

  try {
    const upcomingPage = await fetchListings({
      sort: "starts_at",
      order: "asc",
      limit: 3,
    });
    // Only feature listings with real dates (skip on-demand for this section).
    featured = upcomingPage.items.filter((l) => l.starts_at !== null);
  } catch {
    // Render the page with empty data on backend failure.
  }

  return (
    <main className="bg-white">
      {/* ===== HERO ===== */}
      <section className="max-w-6xl mx-auto px-6 py-24 md:py-32">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          Veterinary Dental CE
        </p>
        <h1 className="mt-4 text-5xl md:text-7xl font-extrabold text-ink-900 max-w-3xl">
          Find your next dental CE
          <br />
          in seconds<span className="text-brand-500">.</span>
        </h1>
        <p className="mt-6 text-xl text-ink-600 max-w-2xl">
          The first aggregator built for veterinary dental continuing education.
          Filter by topic, RACE credits, audience, and format.
        </p>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            href="/listings"
            className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-8 py-4 font-semibold transition-colors"
          >
            Browse Listings →
          </Link>
          <Link
            href="#how-it-works"
            className="rounded-pill border border-ink-200 hover:border-ink-400 text-ink-900 px-8 py-4 font-semibold transition-colors"
          >
            How It Works
          </Link>
        </div>
      </section>

      {/* ===== FEATURED LISTINGS (only if we have any) ===== */}
      {featured.length > 0 && (
        <section className="bg-brand-100/40 border-y border-brand-100">
          <div className="max-w-6xl mx-auto px-6 py-20">
            <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
              <div>
                <p className="text-brand-600 font-semibold uppercase tracking-wide text-sm">
                  Upcoming
                </p>
                <h2 className="mt-3 text-3xl md:text-4xl font-extrabold text-ink-900">
                  Coming up soon<span className="text-brand-500">.</span>
                </h2>
              </div>
              <Link
                href="/listings?sort=starts_at&order=asc"
                className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
              >
                See all upcoming events →
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {featured.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ===== HOW IT WORKS ===== */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-24">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          How It Works
        </p>
        <h2 className="mt-3 text-3xl md:text-4xl font-extrabold text-ink-900 max-w-2xl">
          Built for dental practitioners<span className="text-brand-500">.</span>
        </h2>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            number="01"
            title="Dental-focused"
            description="We aggregate CE across providers and automatically surface only what's relevant to veterinary dentistry. Periodontics, oral surgery, anesthesia for dental procedures, and more."
          />
          <FeatureCard
            number="02"
            title="Real filters"
            description="Filter by RACE-approved status, credit hours, audience, format, and dental subcategory. Find what counts toward your renewal in seconds."
          />
          <FeatureCard
            number="03"
            title="Always current"
            description="Our scrapers run automatically and the catalog refreshes daily. No stale listings, no expired events."
          />
        </div>
      </section>

      {/* ===== BOTTOM CTA ===== */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl md:text-4xl font-extrabold text-ink-900">
          Ready to find your next dental CE<span className="text-brand-500">?</span>
        </h2>
        <p className="mt-4 text-lg text-ink-600 max-w-xl mx-auto">
          Browse the catalog and filter by what matters to you.
        </p>
        <div className="mt-8">
          <Link
            href="/listings"
            className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-10 py-4 font-semibold transition-colors inline-block"
          >
            Browse Listings →
          </Link>
        </div>
      </section>
    </main>
  );
}

// ===== Subcomponents =====

function FeatureCard({
  number,
  title,
  description,
}: {
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl bg-white border border-ink-100 p-8 shadow-card hover:shadow-cardHover transition-shadow">
      <p className="text-brand-500 font-extrabold text-2xl">{number}</p>
      <h3 className="mt-3 text-xl font-bold text-ink-900">{title}</h3>
      <p className="mt-3 text-ink-600 leading-relaxed">{description}</p>
    </div>
  );
}
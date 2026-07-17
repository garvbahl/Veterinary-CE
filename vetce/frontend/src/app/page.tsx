import { fetchListings, fetchProviders } from "@/lib/api";
import ListingCard from "@/components/ListingCard";
import Link from "next/link";

export default async function Home() {
  // Fetch everything in parallel.
  let total = 0;
  let featured: Awaited<ReturnType<typeof fetchListings>>["items"] = [];
  let periovive: Awaited<ReturnType<typeof fetchListings>>["items"] = [];
  let providers: Awaited<ReturnType<typeof fetchProviders>> = [];

  try {
    const [allListings, upcomingPage, periovivePage, providersList] = await Promise.all([
      fetchListings({ limit: 1 }),
      fetchListings({ sort: "starts_at", order: "asc", limit: 3 }),
      fetchListings({ provider: "periovive", sort: "id", order: "desc", limit: 3 }),
      fetchProviders(),
    ]);
    total = allListings.total;
    // Only show listings that actually have a start date (real upcoming events).
    featured = upcomingPage.items.filter((l) => l.starts_at !== null);
    periovive = periovivePage.items;
    providers = providersList;
  } catch {
    // Render the page with empty data on backend failure — better than crashing.
  }

  // For the "trusted providers" grid: hide empty providers, show the
  // ones with the most listings first, capped to keep the grid tidy.
  const featuredProviders = providers
    .filter((p) => (p.listing_count ?? 0) > 0)
    .sort((a, b) => (b.listing_count ?? 0) - (a.listing_count ?? 0))
    .slice(0, 8);

  return (
    <main className="bg-white">
      {/* ===== HERO ===== */}
      <section className="max-w-6xl mx-auto px-6 py-24 md:py-32">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          Veterinary Dentistry CE
        </p>
        <h1 className="mt-4 text-5xl md:text-7xl font-extrabold text-ink-900 max-w-3xl">
          Find your next CE
          <br />
          in seconds<span className="text-brand-500">.</span>
        </h1>
        <p className="mt-6 text-xl text-ink-600 max-w-2xl">
          A directory of veterinary dentistry continuing education, aggregated by
          PerioVive from providers across the profession. Filter by RACE credits,
          audience, format, and topic.
        </p>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link href="/listings" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-8 py-4 font-semibold transition-colors">
            Browse Listings →
          </Link>
          <Link href="#how-it-works" className="rounded-pill border border-ink-200 hover:border-ink-400 text-ink-900 px-8 py-4 font-semibold transition-colors">
            How It Works
          </Link>
        </div>

        {total > 0 && (
          <p className="mt-8 text-sm text-ink-400">
            Currently tracking{" "}
            <span className="font-semibold text-ink-600">{total}</span>{" "}
            CE listings across {providers.length} provider{providers.length === 1 ? "" : "s"}.
          </p>
        )}
      </section>

      {/* ===== FROM PERIOVIVE ===== */}
      {periovive.length > 0 && (
        <section className="bg-gradient-to-b from-white to-brand-50/30">
          <div className="max-w-6xl mx-auto px-6 py-20">
            <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
              <div>
                <p className="text-brand-600 font-semibold uppercase tracking-wide text-sm">
                  From PerioVive
                </p>
                <h2 className="mt-3 text-3xl md:text-4xl font-extrabold text-ink-900">
                  Our latest courses<span className="text-brand-500">.</span>
                </h2>
                <p className="mt-3 text-ink-600 max-w-xl">
                  Free RACE-approved CE on veterinary dentistry, from our own
                  clinical team and invited specialists.
                </p>
              </div>
              <Link
                href="/listings?provider=periovive"
                className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
              >
                See all PerioVive CE →
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {periovive.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ===== FEATURED LISTINGS ===== */}
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
              <Link href="/listings?sort=starts_at&order=asc" className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors">
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
          Built for finding CE fast<span className="text-brand-500">.</span>
        </h2>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            number="01"
            title="One place"
            description="Stop checking five provider sites every month. We aggregate listings from the providers vets and techs actually use."
          />
          <FeatureCard
            number="02"
            title="Real filters"
            description="Filter by RACE-approved status, credit hours, audience, and format. Find what counts toward your renewal in seconds."
          />
          <FeatureCard
            number="03"
            title="Always current"
            description="Our scrapers run automatically and the data updates daily. No stale catalogs."
          />
        </div>
      </section>

      {/* ===== PROVIDERS ===== */}
      {providers.length > 0 && (
        <section className="bg-ink-50/40 border-t border-ink-100">
          <div className="max-w-6xl mx-auto px-6 py-20 text-center">
            <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
              Sources
            </p>
            <h2 className="mt-3 text-3xl md:text-4xl font-extrabold text-ink-900">
              Aggregated from trusted providers<span className="text-brand-500">.</span>
            </h2>
            <p className="mt-4 text-lg text-ink-600 max-w-2xl mx-auto">
              We pull listings directly from the providers' own catalogs. No third parties, no scraped review sites — just the source.
            </p>

            <div className="mt-12 flex flex-wrap items-center justify-center gap-6">
                {featuredProviders.map((p) => (
                <Link
                  key={p.slug}
                  href={`/listings?provider=${p.slug}`}
                  className="rounded-2xl border border-ink-200 bg-white px-8 py-6 hover:border-brand-300 hover:shadow-card transition-all min-w-[180px]"
                >
                  <p className="text-lg font-bold text-ink-900">{p.name}</p>
                  {p.listing_count !== null && (
                    <p className="mt-1 text-sm text-ink-400">
                      {p.listing_count} listing{p.listing_count === 1 ? "" : "s"}
                    </p>
                  )}
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ===== BOTTOM CTA ===== */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl md:text-4xl font-extrabold text-ink-900">
          Ready to find your next CE<span className="text-brand-500">?</span>
        </h2>
        <p className="mt-4 text-lg text-ink-600 max-w-xl mx-auto">
          {total > 0
            ? `Browse ${total} listings now. Filter by what matters to you.`
            : "Browse all listings now. Filter by what matters to you."}
        </p>
        <div className="mt-8">
          <Link href="/listings" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-10 py-4 font-semibold transition-colors inline-block">
            Browse Listings →
          </Link>
        </div>
      </section>
    </main>
  );
}

// ===== Subcomponents =====

function FeatureCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="rounded-2xl bg-white border border-ink-100 p-8 shadow-card hover:shadow-cardHover transition-shadow">
      <p className="text-brand-500 font-extrabold text-2xl">{number}</p>
      <h3 className="mt-3 text-xl font-bold text-ink-900">{title}</h3>
      <p className="mt-3 text-ink-600 leading-relaxed">{description}</p>
    </div>
  );
}
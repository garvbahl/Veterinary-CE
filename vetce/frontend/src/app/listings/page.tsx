import { fetchListings, fetchProviders } from "@/lib/api";
import ListingCard from "@/components/ListingCard";
import SearchBar from "@/components/SearchBar";
import FilterSidebar from "@/components/FilterSidebar";
import SortSelect from "@/components/SortSelect";
import type { ListingsQuery, ListingsPage, Provider } from "@/lib/types";
import { CATEGORY_OPTIONS } from "@/lib/categories";

export const metadata = {
  title: "Browse CE — Veterinary Dentistry CE, aggregated by PerioVive",
  description: "Browse veterinary dentistry continuing education listings aggregated from providers across the profession.",
};

// Hardcoded for now ΓÇö these match what our scrapers produce.
// In Step 6.5 we could fetch these dynamically from the database, but the set
// is small and changes infrequently.
const AUDIENCE_OPTIONS = [
  { value: "vets", label: "Veterinarians" },
  { value: "techs", label: "Technicians" },
  { value: "vets and techs", label: "Both" },
];

const FORMAT_OPTIONS = [
  { value: "live", label: "Live" },
  { value: "on_demand", label: "On Demand" },
  { value: "hybrid", label: "Hybrid" },
];

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ListingsPage({ searchParams }: PageProps) {
  // Next.js 15+ makes searchParams a Promise; await it.
  const params = await searchParams;

  // Build the query from URL params, casting to the right types.
  const query: ListingsQuery = {
    limit: 50,
    sort: (params.sort as ListingsQuery["sort"]) ?? "starts_at",
    order: (params.order as ListingsQuery["order"]) ?? "asc",
  };
  if (typeof params.provider === "string") query.provider = params.provider;
  if (typeof params.audience === "string") query.audience = params.audience;
  if (typeof params.format === "string") query.format = params.format;
  if (typeof params.category === "string") query.category = params.category;
  if (typeof params.min_credits === "string") {
    const n = Number(params.min_credits);
    if (!Number.isNaN(n)) query.min_credits = n;
  }
  if (typeof params.q === "string") query.q = params.q;
  

  // Fetch listings (filtered) and providers (for the sidebar) in parallel.
 // Fetch listings (filtered) and providers (for the sidebar) in parallel.
  let page: ListingsPage | null = null;
  let providers: Provider[] = [];
  let error: string | null = null;

  try {
    [page, providers] = await Promise.all([
      fetchListings(query),
      fetchProviders(),
    ]);
  } catch (e) {
    error = (e as Error).message;
  }

  const providerOptions = providers.map((p) => ({
    value: p.slug,
    label: p.name,
    count: p.listing_count ?? undefined,
  }));

  return (
    <main className="bg-ink-50/40 min-h-screen">
      {/* Page header */}
      <section className="bg-white border-b border-ink-100">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
            Browse
          </p>
          <h1 className="mt-3 text-4xl md:text-5xl font-extrabold text-ink-900">
            Veterinary Dentistry CE<span className="text-brand-500">.</span>
          </h1>
          <p className="mt-4 text-lg text-ink-600 max-w-2xl">
            A directory of veterinary dentistry continuing education, aggregated
            by PerioVive from providers across the profession. Use the filters to
            narrow down by provider, audience, format, or credits.
          </p>

          {/* Search bar */}
          <div className="mt-8 max-w-2xl">
            <SearchBar />
          </div>
        </div>
      </section>

      {/* Main: sidebar + grid */}
      <section className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-10">
        {/* Sidebar */}
        <FilterSidebar
          providers={providerOptions}
          audiences={AUDIENCE_OPTIONS}
          formats={FORMAT_OPTIONS}
          categories={CATEGORY_OPTIONS}
        />

        {/* Content */}
        <div>
          {/* Results header */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
            <p className="text-sm text-ink-600">
              {page ? (
                <>
                  Showing{" "}
                  <span className="font-semibold text-ink-900">
                    {page.items.length}
                  </span>{" "}
                  of{" "}
                  <span className="font-semibold text-ink-900">
                    {page.total}
                  </span>{" "}
                  listings
                </>
              ) : (
                "—"
              )}
            </p>
            <SortSelect />
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">
              <p className="font-semibold">Could not load listings</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {/* Empty */}
          {page && page.items.length === 0 && (
            <div className="rounded-xl border border-ink-200 bg-white p-12 text-center">
              <p className="text-ink-900 font-semibold">No listings match your filters.</p>
              <p className="text-ink-600 text-sm mt-2">
                Try removing some filters or clearing all to start over.
              </p>
            </div>
          )}

          {/* Grid */}
          {page && page.items.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {page.items.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

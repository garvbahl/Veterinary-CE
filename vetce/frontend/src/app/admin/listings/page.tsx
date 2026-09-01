"use client";
/**
 * /admin/listings — browse and edit all listings.
 *
 * Client component. Fetches admin listings (recent first), lets you filter by
 * title, and links each row to its edit page. Same auth pattern as the rest of
 * admin: a 401 redirects to /admin/login.
 */
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError, fetchAdminListings } from "@/lib/api";
import type { Listing } from "@/lib/types";

// How many listings to pull. The admin endpoint returns a plain array; this is
// a practical ceiling for browsing/editing (recent listings matter most, and
// the filter box finds older ones by title).
const FETCH_LIMIT = 300;

export default function AdminListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await fetchAdminListings(FETCH_LIMIT);
        if (cancelled) return;
        setListings(rows);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/admin/login");
          return;
        }
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return listings;
    return listings.filter((l) => l.title.toLowerCase().includes(q));
  }, [listings, filter]);

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Listings</h1>
        <p className="mt-6 text-ink-500">Loading listings…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Listings</h1>
        <div className="mt-6 rounded-2xl bg-red-50 px-6 py-4 ring-1 ring-red-200">
          <div className="font-semibold text-red-700">Failed to load listings.</div>
          <div className="mt-1 text-sm text-red-600">{error}</div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-baseline justify-between">
        <h1 className="text-3xl font-bold text-ink-900">
          Listings<span className="text-brand-500">.</span>
        </h1>
        <div className="flex items-center gap-6 text-sm text-ink-500">
          <Link href="/admin" className="hover:text-brand-600">
            ← Back to Admin
          </Link>
          <Link href="/admin/listings/new" className="hover:text-brand-600">
            + Add listing
          </Link>
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by title…"
          className="w-full max-w-sm rounded-lg border border-ink-200 px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
        />
        <span className="whitespace-nowrap text-sm text-ink-500">
          {filtered.length} of {listings.length}
        </span>
      </div>

      <div className="overflow-hidden rounded-2xl ring-1 ring-ink-100">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Title</th>
              <th className="px-4 py-3 font-semibold">Provider</th>
              <th className="px-4 py-3 font-semibold">Date</th>
              <th className="px-4 py-3 font-semibold"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {filtered.map((l) => (
              <tr key={l.id} className="hover:bg-ink-50/50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ink-900">{l.title}</span>
                    {l.featured && (
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-600">
                        Featured
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-ink-600">{l.provider}</td>
                <td className="px-4 py-3 text-ink-600">
                  {l.starts_at ? l.starts_at.slice(0, 10) : "On-Demand"}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/admin/listings/${l.id}/edit`}
                    className="font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Edit →
                  </Link>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-ink-400">
                  No listings match “{filter}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
"use client";
/**
 * /admin — operations dashboard.
 *
 * Server component. Parallel-fetches three datasets:
 *   1. Dashboard summary (totals, 24h activity, health verdict)
 *   2. Per-source status (4 rows)
 *   3. Recent scrape runs (last 20)
 *
 * No auth. Lives at an undocumented URL; we'll add auth before deploy.
 */
import Link from "next/link";

import { HealthIndicator } from "@/components/HealthIndicator";
import { RunStatusBadge } from "@/components/RunStatusBadge";
import {
  ApiError,
  fetchDashboardSummary,
  fetchAdminListings,
  fetchScrapeRuns,
  fetchSourceStatuses,
} from "@/lib/api";
import { absoluteTime, formatDuration, relativeTime } from "@/lib/time";
import type { DashboardSummary, ScrapeRun, SourceStatus } from "@/lib/types";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogoutButton } from "@/components/LogoutButton";


export default function AdminPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [recentListings, setRecentListings] = useState<Awaited<ReturnType<typeof fetchAdminListings>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, src, r, recent] = await Promise.all([
          fetchDashboardSummary(),
          fetchSourceStatuses(),
          fetchScrapeRuns({ limit: 20 }),
          fetchAdminListings(15),
        ]);
        if (cancelled) return;
        setSummary(s);
        setSources(src);
        setRuns(r);
        setRecentListings(recent);
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

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Admin</h1>
        <p className="mt-6 text-ink-500">Loading dashboard…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Admin</h1>
        <div className="mt-6 rounded-2xl bg-red-50 px-6 py-4 ring-1 ring-red-200">
          <div className="font-semibold text-red-700">Failed to load dashboard.</div>
          <div className="mt-1 text-sm text-red-600">{error}</div>
        </div>
      </main>
    );
  }
  if (!summary) {
    return null;
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-baseline justify-between">
        <h1 className="text-3xl font-bold text-ink-900">
          Operations<span className="text-brand-500">.</span>
        </h1>
       <div className="flex items-center gap-6 text-sm text-ink-500">
          <Link href="/listings" className="hover:text-brand-600">
            ← back to listings
          </Link>
          <Link
            href="/admin/listings/new"
            className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 text-sm font-semibold transition-colors"
          >
            + Add Listing
          </Link>
          <LogoutButton />
        </div>
      </div>

      {/* Section 1: Status cards */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          label="Total listings"
          value={summary.total_listings.toLocaleString()}
          sublabel={`${summary.duplicate_listings} dedup'd`}
        />
        <StatusCard
          label="Runs (last 24h)"
          value={summary.runs_last_24h_total.toLocaleString()}
          sublabel={runActivityBreakdown(summary)}
        />
        <StatusCard
          label="Providers"
          value={summary.by_provider.length.toString()}
          sublabel={summary.by_provider
            .slice(0, 4)
            .map((p) => `${p.provider_name} (${p.listing_count})`)
            .join(", ")}
        />
        <div className="rounded-2xl bg-white p-5 shadow-card ring-1 ring-ink-100">
          <div className="mb-3 text-xs font-medium uppercase tracking-wide text-ink-500">
            System health
          </div>
          <HealthIndicator
            status={summary.health_status}
            reason={summary.health_reason}
          />
        </div>
      </section>

      {/* Section 2: Per-source status */}
      <section className="mt-10">
        <h2 className="mb-4 text-xl font-bold text-ink-900">Sources</h2>
        <div className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-ink-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-xs font-medium uppercase tracking-wide text-ink-600">
              <tr>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3">Listings</th>
                <th className="px-5 py-3">Last run</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Last success</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {sources.map((s) => (
                <tr key={s.source_id}>
                  <td className="px-5 py-4">
                    <div className="font-semibold text-ink-900">{s.provider_name}</div>
                    <div className="text-xs text-ink-500">{s.source_slug}</div>
                  </td>
                  <td className="px-5 py-4 text-ink-900">{s.listing_count}</td>
                  <td className="px-5 py-4">
                    <div
                      className="text-ink-700"
                      title={absoluteTime(s.last_run_started_at)}
                    >
                      {relativeTime(s.last_run_started_at)}
                    </div>
                    {s.last_run_duration_seconds != null && (
                      <div className="text-xs text-ink-500">
                        {formatDuration(s.last_run_duration_seconds)}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <RunStatusBadge status={s.last_run_status} />
                    {s.last_error_message && (
                      <div className="mt-1 max-w-xs truncate text-xs text-red-600" title={s.last_error_message}>
                        {s.last_error_message}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-4 text-ink-700" title={absoluteTime(s.last_successful_run_at)}>
                    {relativeTime(s.last_successful_run_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section: Recent listings (with edit links) */}
      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-ink-900">Recent listings</h2>
          <Link
            href="/admin/listings"
            className="text-sm font-semibold text-brand-600 hover:text-brand-700"
          >
            See all →
          </Link>
        </div>
        <div className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-ink-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-xs font-medium uppercase tracking-wide text-ink-600">
              <tr>
                <th className="px-5 py-3">Title</th>
                <th className="px-5 py-3">Provider</th>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3">Starts</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {recentListings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-ink-500">
                    No listings yet.
                  </td>
                </tr>
              ) : (
                recentListings.map((l) => (
                  <tr key={l.id}>
                    <td className="px-5 py-3 text-ink-900 max-w-md truncate" title={l.title}>
                      {l.title}
                    </td>
                    <td className="px-5 py-3 text-ink-700">{l.provider}</td>
                    <td className="px-5 py-3 text-xs text-ink-500">{l.source}</td>
                    <td className="px-5 py-3 text-ink-700">
                      {l.subject_category ?? <span className="text-ink-400">—</span>}
                    </td>
                    <td className="px-5 py-3 text-ink-700">
                      {l.starts_at ?? <span className="text-ink-400">on demand</span>}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        href={`/admin/listings/${l.id}/edit`}
                        className="text-sm font-semibold text-brand-600 hover:text-brand-700"
                      >
                        Edit
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 3: Recent runs */}
      <section className="mt-10">
        <h2 className="mb-4 text-xl font-bold text-ink-900">Recent runs</h2>
        <div className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-ink-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-xs font-medium uppercase tracking-wide text-ink-600">
              <tr>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3">Started</th>
                <th className="px-5 py-3">Duration</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Inserted</th>
                <th className="px-5 py-3">Updated</th>
                <th className="px-5 py-3">Errored</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-ink-500">
                    No scrape runs recorded yet.
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id}>
                    <td className="px-5 py-3 font-medium text-ink-900">
                      {r.source_slug}
                    </td>
                    <td className="px-5 py-3 text-ink-700" title={absoluteTime(r.started_at)}>
                      {relativeTime(r.started_at)}
                    </td>
                    <td className="px-5 py-3 text-ink-700">
                      {formatDuration(r.duration_seconds)}
                    </td>
                    <td className="px-5 py-3">
                      <RunStatusBadge status={r.status} />
                      {r.error_message && (
                        <div className="mt-1 max-w-xs truncate text-xs text-red-600" title={r.error_message}>
                          {r.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3 text-ink-700">{r.listings_inserted}</td>
                    <td className="px-5 py-3 text-ink-700">{r.listings_updated}</td>
                    <td className="px-5 py-3 text-ink-700">{r.listings_errored}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

// ============================================================
// Local helpers
// ============================================================

function StatusCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string;
  sublabel?: string;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-card ring-1 ring-ink-100">
      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-500">
        {label}
      </div>
      <div className="text-3xl font-bold text-ink-900">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-ink-500">{sublabel}</div>}
    </div>
  );
}

function runActivityBreakdown(summary: DashboardSummary): string {
  const parts: string[] = [];
  if (summary.runs_last_24h_success) parts.push(`${summary.runs_last_24h_success} ok`);
  if (summary.runs_last_24h_partial) parts.push(`${summary.runs_last_24h_partial} partial`);
  if (summary.runs_last_24h_failed) parts.push(`${summary.runs_last_24h_failed} failed`);
  if (summary.runs_last_24h_running) parts.push(`${summary.runs_last_24h_running} running`);
  return parts.length ? parts.join(", ") : "no activity";
}
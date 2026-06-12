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
  fetchScrapeRuns,
  fetchSourceStatuses,
} from "@/lib/api";
import { absoluteTime, formatDuration, relativeTime } from "@/lib/time";
import type { DashboardSummary, ScrapeRun, SourceStatus } from "@/lib/types";
import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/LogoutButton";


export const metadata = {
  title: "Admin — PerioVive CE",
  robots: { index: false, follow: false },
};

export default async function AdminPage() {
  let summary: DashboardSummary | null = null;
  let sources: SourceStatus[] = [];
  let runs: ScrapeRun[] = [];

  try {
    const [s, src, r] = await Promise.all([
      fetchDashboardSummary(),
      fetchSourceStatuses(),
      fetchScrapeRuns({ limit: 20 }),
    ]);
    summary = s;
    sources = src;
    runs = r;
  } catch (err) {
    // If the error is "Not authenticated" (401), redirect to login.
    // Server components can call redirect() to trigger a redirect response.
    if (err instanceof ApiError && err.status === 401) {
      redirect("/admin/login");
    }

    return (
      <main className="mx-auto max-w-6xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Admin</h1>
        <div className="mt-6 rounded-2xl bg-red-50 px-6 py-4 ring-1 ring-red-200">
          <div className="font-semibold text-red-700">Failed to load dashboard.</div>
          <div className="mt-1 text-sm text-red-600">
            {(err as Error).message}
          </div>
        </div>
      </main>
    );
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
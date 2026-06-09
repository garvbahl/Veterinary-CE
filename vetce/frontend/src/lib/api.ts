/**
 * API client for the vetce backend.
 *
 * All functions return Promises and throw on non-2xx responses.
 * The thrown error is an ApiError instance with status and detail.
 *
 * Usage:
 *   import { fetchListings, fetchListing } from "@/lib/api";
 *   const page = await fetchListings({ provider: "navta", limit: 20 });
 */
import type {
  DashboardSummary,
  Listing,
  ListingsPage,
  ListingsQuery,
  Provider,
  ScrapeRun,
  Source,
  SourceStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Internal: perform a GET request and parse the JSON response.
 * Throws ApiError on non-2xx responses.
 */
async function apiGet<T>(path: string, query?: Record<string, unknown>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "GET",
      headers: { Accept: "application/json" },
      // Tell Next.js not to cache by default — we always want fresh data.
      // Pages that want caching can override per-call.
      cache: "no-store",
    });
  } catch (networkErr) {
    // fetch() throws only on network failure (server down, DNS error, etc.)
    throw new ApiError(
      0,
      networkErr,
      `Network error contacting ${url.host}: ${(networkErr as Error).message}`,
    );
  }

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      // response body wasn't JSON
    }
    throw new ApiError(
      response.status,
      detail,
      `API ${response.status} on ${path}`,
    );
  }

  return (await response.json()) as T;
}

// ===== Listings =====

export function fetchListings(query?: ListingsQuery): Promise<ListingsPage> {
  return apiGet<ListingsPage>("/api/v1/listings", query);
}

export function fetchListing(id: number): Promise<Listing> {
  return apiGet<Listing>(`/api/v1/listings/${id}`);
}

// ===== Providers =====

export function fetchProviders(): Promise<Provider[]> {
  return apiGet<Provider[]>("/api/v1/providers");
}

export function fetchProvider(slug: string): Promise<Provider> {
  return apiGet<Provider>(`/api/v1/providers/${slug}`);
}

// ===== Sources =====

export function fetchSources(): Promise<Source[]> {
  return apiGet<Source[]>("/api/v1/sources");
}

export function fetchSource(slug: string): Promise<Source> {
  return apiGet<Source>(`/api/v1/sources/${slug}`);
}

// ===== Scrape runs =====

export function fetchScrapeRuns(query?: {
  limit?: number;
  source?: string;
  status?: string;
}): Promise<ScrapeRun[]> {
  return apiGet<ScrapeRun[]>("/api/v1/scrape_runs", query);
}

// ===== Dashboard (admin) =====

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/api/v1/scrape_runs/dashboard");
}

export function fetchSourceStatuses(): Promise<SourceStatus[]> {
  return apiGet<SourceStatus[]>("/api/v1/scrape_runs/by-source");
}

// ===== Meta =====

export function fetchHealth(): Promise<{ ok: boolean; now: string }> {
  return apiGet<{ ok: boolean; now: string }>("/health");
}


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
  SubscriberCreateResponse,
  AdminMeResponse,
  AdminLoginResponse,
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
 * Read cookies from the incoming request when running on the server.
 *
 * In a Next.js Server Component, the browser's request cookies are
 * available via next/headers. In the browser, cookies are sent
 * automatically via `credentials: "include"`.
 *
 * Returns an empty string when called from the browser.
 */
async function getServerCookieHeader(): Promise<string> {
  if (typeof window !== "undefined") {
    return ""; // browser — cookies sent via credentials: "include"
  }
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    return cookieStore
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");
  } catch {
    return "";
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

  const headers: Record<string, string> = { Accept: "application/json" };
  const cookieHeader = await getServerCookieHeader();
  if (cookieHeader) {
    headers["Cookie"] = cookieHeader;
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "GET",
      headers,
      cache: "no-store",
      credentials: "include",
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

// ===== Subscribers =====

export async function subscribeEmail(email: string): Promise<SubscriberCreateResponse> {
  const url = new URL(`${API_BASE}/api/v1/subscribers`);

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      cache: "no-store",
      body: JSON.stringify({ email }),
    });
  } catch (networkErr) {
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
      // body wasn't JSON
    }
    const detailObj = detail as { detail?: string } | null;
    throw new ApiError(
      response.status,
      detail,
      detailObj?.detail ?? `API ${response.status} on /subscribers`,
    );
  }

  return (await response.json()) as SubscriberCreateResponse;
}

// ===== Admin: Listings (manual entry) =====

export type ManualSource = {
  id: number;
  slug: string;
  provider_name: string;
};

export type ListingCreatePayload = {
  source_id: number;
  title: string;
  source_url: string;
  description?: string | null;
  starts_at?: string | null; // YYYY-MM-DD
  ends_at?: string | null;
  format?: string | null;
  cost?: string | null;
  race_approved?: boolean | null;
  credit_hours?: number | null;
  presenter?: string | null;
  audience?: string | null;
  registration_url?: string | null;
  subject_category?: string | null;
};

export function fetchManualSources(): Promise<ManualSource[]> {
  return apiGet<ManualSource[]>("/api/v1/admin/sources/manual");
}

export type ListingUpdatePayload = Partial<Omit<ListingCreatePayload, "source_id">> & {
  status?: string;
  featured?: boolean;
  featured_rank?: number | null;
};

export function fetchAdminListings(limit = 50): Promise<Listing[]> {
  return apiGet<Listing[]>("/api/v1/admin/listings", { limit });
}

export async function updateListing(
  id: number,
  payload: ListingUpdatePayload,
): Promise<Listing> {
  const url = new URL(`${API_BASE}/api/v1/admin/listings/${id}`);
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      cache: "no-store",
      credentials: "include",
      body: JSON.stringify(payload),
    });
  } catch (networkErr) {
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
      // body wasn't JSON
    }
    const detailObj = detail as { detail?: string } | null;
    throw new ApiError(
      response.status,
      detail,
      detailObj?.detail ?? `API ${response.status} on /admin/listings/${id}`,
    );
  }
  return (await response.json()) as Listing;
}

export async function createListing(
  payload: ListingCreatePayload,
): Promise<Listing> {
  const url = new URL(`${API_BASE}/api/v1/admin/listings`);
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      cache: "no-store",
      credentials: "include",
      body: JSON.stringify(payload),
    });
  } catch (networkErr) {
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
      // body wasn't JSON
    }
    const detailObj = detail as { detail?: string } | null;
    throw new ApiError(
      response.status,
      detail,
      detailObj?.detail ?? `API ${response.status} on /admin/listings`,
    );
  }
  return (await response.json()) as Listing;
}

// ===== Admin auth =====

export async function adminLogin(password: string): Promise<AdminLoginResponse> {
  const url = new URL(`${API_BASE}/api/v1/admin/login`);

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      cache: "no-store",
      credentials: "include",
      body: JSON.stringify({ password }),
    });
  } catch (networkErr) {
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
      // body wasn't JSON
    }
    const detailObj = detail as { detail?: string } | null;
    throw new ApiError(
      response.status,
      detail,
      detailObj?.detail ?? `API ${response.status} on /admin/login`,
    );
  }

  return (await response.json()) as AdminLoginResponse;
}

export async function adminLogout(): Promise<void> {
  const url = new URL(`${API_BASE}/api/v1/admin/logout`);
  try {
    await fetch(url.toString(), {
      method: "POST",
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    // Best-effort. Even if logout fails server-side, we'll clear UI state anyway.
  }
}

export async function adminMe(): Promise<AdminMeResponse> {
  return apiGet<AdminMeResponse>("/api/v1/admin/me");
}

// ===== Meta =====

export function fetchHealth(): Promise<{ ok: boolean; now: string }> {
  return apiGet<{ ok: boolean; now: string }>("/health");
}


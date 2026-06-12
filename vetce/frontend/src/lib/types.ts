/**
 * TypeScript types mirroring the backend's Pydantic schemas.
 *
 * Keep these in sync with src/vetce/api/schemas.py on the backend.
 * In the future, these could be auto-generated from /openapi.json.
 */

export type Listing = {
  id: number;
  title: string;
  provider: string;
  source: string;
  description: string | null;
  source_url: string;
  registration_url: string | null;

  starts_at: string | null;   // ISO date string, e.g. "2026-10-09"
  ends_at: string | null;

  format: string | null;      // "live" | "on_demand" | "hybrid"
  cost: string | null;
  race_approved: boolean | null;
  race_program_number: string | null;
  credit_hours: number | null;
  presenter: string | null;
  audience: string | null;
  delivery_method: string | null;
  subject_category: string | null;
};

export type ListingsPage = {
  items: Listing[];
  total: number;
  limit: number;
  offset: number;
};

export type Provider = {
  id: number;
  slug: string;
  name: string;
  website: string | null;
  listing_count: number | null;
};

export type Source = {
  id: number;
  slug: string;
  kind: string;
  description: string | null;
  cron_expression: string | null;
  provider_slug: string;
  listing_count: number | null;
};

export type ScrapeRun = {
  id: number;
  source_slug: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  listings_inserted: number;
  listings_updated: number;
  listings_errored: number;
  error_message: string | null;
};

/**
 * Query parameters accepted by GET /api/v1/listings.
 * All fields optional — pass only what you want to filter on.
 */
export type ListingsQuery = {
  limit?: number;
  offset?: number;
  provider?: string;
  source?: string;
  audience?: string;
  format?: string;
  min_credits?: number;
  max_credits?: number;
  q?: string;
  sort?: "id" | "title" | "starts_at" | "credit_hours";
  order?: "asc" | "desc";
};

// ============================================================
// Dashboard / Operations
// ============================================================

export interface ProviderListingCount {
  provider_slug: string;
  provider_name: string;
  listing_count: number;
}

export interface DashboardSummary {
  total_listings: number;
  duplicate_listings: number;
  canonical_listings: number;

  runs_last_24h_total: number;
  runs_last_24h_success: number;
  runs_last_24h_partial: number;
  runs_last_24h_failed: number;
  runs_last_24h_running: number;

  by_provider: ProviderListingCount[];

  health_status: "green" | "yellow" | "red";
  health_reason: string | null;
}

export interface SourceStatus {
  source_id: number;
  source_slug: string;
  provider_slug: string;
  provider_name: string;
  listing_count: number;

  last_run_started_at: string | null;     // ISO datetime
  last_run_finished_at: string | null;    // ISO datetime
  last_run_status: string | null;
  last_run_duration_seconds: number | null;

  last_successful_run_at: string | null;  // ISO datetime
  last_error_message: string | null;
}

// ============================================================
// Subscribers
// ============================================================

export interface SubscriberCreateResponse {
  ok: boolean;
  already_subscribed: boolean;
}

// ============================================================
// Admin auth
// ============================================================

export interface AdminLoginResponse {
  ok: boolean;
}

export interface AdminMeResponse {
  authenticated: boolean;
}
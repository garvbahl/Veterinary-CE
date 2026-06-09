/**
 * Time formatting helpers for the dashboard.
 *
 * All functions accept ISO datetime strings (from API responses) or null.
 * Return null/sensible defaults for null input.
 */

/**
 * Format an ISO datetime as "2 minutes ago", "3 hours ago", "5 days ago".
 *
 * Returns "never" for null input. Doesn't try to be cute past a week —
 * just shows the absolute date.
 */
export function relativeTime(iso: string | null): string {
  if (!iso) return "never";

  const then = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();

  if (diffMs < 0) {
    // Clock skew or future timestamp — just show absolute
    return then.toLocaleString();
  }

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return `${seconds}s ago`;
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;

  return then.toLocaleDateString();
}

/**
 * Format an ISO datetime as an absolute timestamp suitable for a tooltip.
 *
 * Returns "—" for null input.
 */
export function absoluteTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

/**
 * Format a duration in seconds as "1m 23s" or "45s".
 *
 * Returns "—" for null input.
 */
export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60);
  return `${minutes}m ${remaining}s`;
}
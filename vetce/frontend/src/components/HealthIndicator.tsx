/**
 * Big health indicator for the dashboard hero.
 *
 * Shows a colored dot, a label, and an optional reason.
 */
type Props = {
  status: "green" | "yellow" | "red";
  reason: string | null;
};

const CONFIG: Record<Props["status"], { label: string; dot: string; text: string; bg: string }> = {
  green: {
    label: "Healthy",
    dot: "bg-emerald-500",
    text: "text-emerald-700",
    bg: "bg-emerald-50 ring-emerald-200",
  },
  yellow: {
    label: "Degraded",
    dot: "bg-amber-500",
    text: "text-amber-700",
    bg: "bg-amber-50 ring-amber-200",
  },
  red: {
    label: "Critical",
    dot: "bg-red-500",
    text: "text-red-700",
    bg: "bg-red-50 ring-red-200",
  },
};

export function HealthIndicator({ status, reason }: Props) {
  const config = CONFIG[status];

  return (
    <div className={`flex items-center gap-3 rounded-2xl ${config.bg} px-4 py-3 ring-1`}>
      <span className={`inline-block size-3 rounded-full ${config.dot}`} aria-hidden />
      <div>
        <div className={`text-sm font-semibold ${config.text}`}>{config.label}</div>
        <div className="mt-0.5 text-xs text-ink-600">
          {reason ?? "All sources reporting in."}
        </div>
      </div>
    </div>
  );
}
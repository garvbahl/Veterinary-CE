"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

type Option = { value: string; label: string; count?: number };

type FilterSidebarProps = {
  providers: Option[];
  audiences: Option[];
  formats: Option[];
};

export default function FilterSidebar({ providers, audiences, formats }: FilterSidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);

  function setParam(key: string, value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === null || value === "") {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    params.delete("offset");
    router.push(`/listings?${params.toString()}`);
  }

  const currentProvider = searchParams.get("provider") ?? "";
  const currentAudience = searchParams.get("audience") ?? "";
  const currentFormat = searchParams.get("format") ?? "";
  const currentMinCredits = searchParams.get("min_credits") ?? "";

  const hasActiveFilters = !!(currentProvider || currentAudience || currentFormat || currentMinCredits);

  return (
    <>
      {/* Mobile toggle — only shown on small screens */}
      <button
        type="button"
        onClick={() => setMobileOpen((v) => !v)}
        className="lg:hidden w-full mb-4 rounded-pill border border-ink-200 bg-white px-6 py-3 text-sm font-semibold text-ink-900 hover:border-ink-400 transition-colors flex items-center justify-between"
      >
        <span>
          Filters{hasActiveFilters && <span className="ml-2 inline-flex items-center justify-center h-5 w-5 rounded-full bg-brand-500 text-white text-xs font-bold">!</span>}
        </span>
        <span className="text-ink-400">{mobileOpen ? "Hide" : "Show"}</span>
      </button>

      <aside className={`space-y-8 ${mobileOpen ? "block" : "hidden"} lg:block`}>
        <FilterGroup title="Provider">
          <RadioOption label="All providers" value="" checked={currentProvider === ""} onChange={() => setParam("provider", null)} />
          {providers.map((opt) => (
            <RadioOption
              key={opt.value}
              label={opt.label}
              count={opt.count}
              value={opt.value}
              checked={currentProvider === opt.value}
              onChange={() => setParam("provider", opt.value)}
            />
          ))}
        </FilterGroup>

        <FilterGroup title="Audience">
          <RadioOption label="Anyone" value="" checked={currentAudience === ""} onChange={() => setParam("audience", null)} />
          {audiences.map((opt) => (
            <RadioOption
              key={opt.value}
              label={opt.label}
              value={opt.value}
              checked={currentAudience === opt.value}
              onChange={() => setParam("audience", opt.value)}
            />
          ))}
        </FilterGroup>

        <FilterGroup title="Format">
          <RadioOption label="Any format" value="" checked={currentFormat === ""} onChange={() => setParam("format", null)} />
          {formats.map((opt) => (
            <RadioOption
              key={opt.value}
              label={opt.label}
              value={opt.value}
              checked={currentFormat === opt.value}
              onChange={() => setParam("format", opt.value)}
            />
          ))}
        </FilterGroup>

        <FilterGroup title="Minimum CE credits">
          <input
            type="number"
            min="0"
            step="0.5"
            placeholder="e.g. 1"
            value={currentMinCredits}
            onChange={(e) => setParam("min_credits", e.target.value || null)}
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
          />
        </FilterGroup>

        {hasActiveFilters && (
          <button onClick={() => router.push("/listings")} className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors">
            Clear all filters
          </button>
        )}
      </aside>
    </>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-bold text-ink-900 uppercase tracking-wide mb-3">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function RadioOption({
  label,
  count,
  value,
  checked,
  onChange,
}: {
  label: string;
  count?: number;
  value: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer text-sm group">
      <input
        type="radio"
        value={value}
        checked={checked}
        onChange={onChange}
        className="h-4 w-4 accent-brand-500 cursor-pointer"
      />
      <span className={`flex-1 ${checked ? "text-ink-900 font-semibold" : "text-ink-600 group-hover:text-ink-900"} transition-colors`}>
        {label}
      </span>
      {count !== undefined && (
        <span className="text-xs text-ink-400">{count}</span>
      )}
    </label>
  );
}
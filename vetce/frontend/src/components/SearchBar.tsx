"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";

/**
 * Search input that updates the URL `q` param after a short debounce.
 * Client component because it needs onChange and router.push.
 */
export default function SearchBar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") ?? "";

  const [value, setValue] = useState(initialQ);

  // Debounce: wait 300ms after the user stops typing, then update the URL.
  // This prevents a server fetch on every keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (value.trim().length >= 2) {
        params.set("q", value.trim());
      } else {
        params.delete("q");
      }
      // Reset to first page on new search.
      params.delete("offset");
      router.push(`/listings?${params.toString()}`);
    }, 300);

    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <div className="relative w-full">
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search by title or description…"
        className="w-full rounded-pill border border-ink-200 bg-white px-6 py-3 pl-12 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
      />
      <svg
        className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-ink-400 pointer-events-none"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0Z" />
      </svg>
    </div>
  );
}
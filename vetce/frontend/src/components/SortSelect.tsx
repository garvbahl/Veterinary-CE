"use client";

import { useRouter, useSearchParams } from "next/navigation";

const OPTIONS = [
  { value: "starts_at:asc", label: "Soonest events first" },
  { value: "starts_at:desc", label: "Furthest-out events first" },
  { value: "credit_hours:desc", label: "Most credits first" },
  { value: "credit_hours:asc", label: "Fewest credits first" },
  { value: "title:asc", label: "Title A → Z" },
  { value: "id:desc", label: "Recently added first" },
];

export default function SortSelect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentSort = searchParams.get("sort") ?? "starts_at";
  const currentOrder = searchParams.get("order") ?? "asc";
  const currentValue = `${currentSort}:${currentOrder}`;

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const [sort, order] = e.target.value.split(":");
    const params = new URLSearchParams(searchParams.toString());
    params.set("sort", sort);
    params.set("order", order);
    router.push(`/listings?${params.toString()}`);
  }

  return (
    <select
      value={currentValue}
      onChange={handleChange}
      className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-900 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all cursor-pointer"
    >
      {OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  );
}
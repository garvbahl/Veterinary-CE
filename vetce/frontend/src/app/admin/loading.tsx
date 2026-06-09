export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 h-8 w-48 animate-pulse rounded bg-ink-100" />

      {/* Status cards skeleton */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-2xl bg-white shadow-card ring-1 ring-ink-100"
          />
        ))}
      </section>

      {/* Sources skeleton */}
      <section className="mt-10">
        <div className="mb-4 h-6 w-24 animate-pulse rounded bg-ink-100" />
        <div className="h-64 animate-pulse rounded-2xl bg-white shadow-card ring-1 ring-ink-100" />
      </section>

      {/* Recent runs skeleton */}
      <section className="mt-10">
        <div className="mb-4 h-6 w-32 animate-pulse rounded bg-ink-100" />
        <div className="h-96 animate-pulse rounded-2xl bg-white shadow-card ring-1 ring-ink-100" />
      </section>
    </main>
  );
}
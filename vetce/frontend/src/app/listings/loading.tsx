export default function Loading() {
  return (
    <main className="bg-ink-50/40 min-h-screen">
      {/* Skeleton header */}
      <section className="bg-white border-b border-ink-100">
        <div className="max-w-6xl mx-auto px-6 py-12 animate-pulse">
          <div className="h-3 w-24 bg-brand-100 rounded" />
          <div className="mt-3 h-12 w-96 bg-ink-100 rounded" />
          <div className="mt-4 h-5 w-2/3 max-w-xl bg-ink-100 rounded" />
          <div className="mt-8 h-12 max-w-2xl bg-ink-100 rounded-pill" />
        </div>
      </section>

      {/* Skeleton sidebar + grid */}
      <section className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-10">
        <aside className="space-y-8 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="h-4 w-24 bg-ink-100 rounded" />
              <div className="mt-3 space-y-2">
                <div className="h-4 w-full bg-ink-50 rounded" />
                <div className="h-4 w-4/5 bg-ink-50 rounded" />
                <div className="h-4 w-3/5 bg-ink-50 rounded" />
              </div>
            </div>
          ))}
        </aside>

        <div>
          <div className="h-5 w-40 bg-ink-100 rounded animate-pulse mb-6" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-ink-100 bg-white p-6 animate-pulse">
      <div className="flex justify-between">
        <div className="h-3 w-20 bg-brand-100 rounded" />
        <div className="h-3 w-24 bg-ink-100 rounded" />
      </div>
      <div className="mt-4 h-5 w-full bg-ink-100 rounded" />
      <div className="mt-2 h-5 w-3/4 bg-ink-100 rounded" />
      <div className="mt-4 space-y-2">
        <div className="h-3 w-full bg-ink-50 rounded" />
        <div className="h-3 w-4/5 bg-ink-50 rounded" />
      </div>
      <div className="mt-4 flex gap-2">
        <div className="h-6 w-20 bg-brand-50 rounded-full" />
        <div className="h-6 w-16 bg-ink-50 rounded-full" />
      </div>
      <div className="mt-6 flex justify-between items-center">
        <div className="h-4 w-24 bg-ink-100 rounded" />
        <div className="h-9 w-24 bg-brand-100 rounded-pill" />
      </div>
    </div>
  );
}
export default function Loading() {
  return (
    <main className="bg-ink-50/40 min-h-screen">
      <div className="max-w-4xl mx-auto px-6 py-12 animate-pulse">
        <div className="h-4 w-32 bg-ink-100 rounded mb-6" />

        <div className="bg-white rounded-2xl border border-ink-100 p-8 md:p-10">
          <div className="h-3 w-24 bg-brand-100 rounded" />
          <div className="mt-3 h-9 w-3/4 bg-ink-100 rounded" />
          <div className="mt-2 h-9 w-1/2 bg-ink-100 rounded" />
          <div className="mt-6 h-5 w-48 bg-ink-100 rounded" />
          <div className="mt-8 flex gap-3">
            <div className="h-12 w-32 bg-brand-100 rounded-pill" />
            <div className="h-12 w-40 bg-ink-100 rounded-pill" />
          </div>
        </div>

        <div className="mt-8 bg-white rounded-2xl border border-ink-100 p-8 md:p-10">
          <div className="h-6 w-40 bg-ink-100 rounded mb-4" />
          <div className="space-y-2">
            <div className="h-4 w-full bg-ink-50 rounded" />
            <div className="h-4 w-full bg-ink-50 rounded" />
            <div className="h-4 w-5/6 bg-ink-50 rounded" />
            <div className="h-4 w-4/6 bg-ink-50 rounded" />
          </div>
        </div>
      </div>
    </main>
  );
}
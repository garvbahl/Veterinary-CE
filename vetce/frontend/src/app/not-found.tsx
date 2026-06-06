import Link from "next/link";

export default function NotFound() {
  return (
    <main className="bg-white min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <div className="text-center px-6 py-24 max-w-xl">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          404
        </p>
        <h1 className="mt-3 text-5xl md:text-6xl font-extrabold text-ink-900">
          Not found<span className="text-brand-500">.</span>
        </h1>
        <p className="mt-6 text-lg text-ink-600">
          We couldn&apos;t find what you were looking for. The listing may have
          been removed by its provider, or the link is mistyped.
        </p>
        <div className="mt-10 flex flex-wrap gap-4 justify-center">
          <Link href="/listings" className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-8 py-4 font-semibold transition-colors">
            Browse all listings →
          </Link>
          <Link href="/" className="rounded-pill border border-ink-200 hover:border-ink-400 text-ink-900 px-8 py-4 font-semibold transition-colors">
            Go home
          </Link>
        </div>
      </div>
    </main>
  );
}
"use client";

import Link from "next/link";

const FOOTER_COLUMNS = [
  {
    title: "Browse",
    links: [
      { label: "All Listings", href: "/listings" },
      { label: "By Provider", href: "/providers" },
      { label: "Upcoming Events", href: "/listings?sort=starts_at&order=asc" },
    ],
  },
  {
    title: "About",
    links: [
      { label: "How it Works", href: "/about" },
      { label: "Coverage", href: "/providers" },
      { label: "Data Sources", href: "/sources" },
    ],
  },
  {
    title: "Periovive",
    links: [
      { label: "Main Site", href: "https://periovive-analytics.com" },
      { label: "CE Webinars", href: "https://periovive-analytics.com/marketing-preview/ce" },
      { label: "Contact", href: "mailto:hello@periovive.com" },
    ],
  },
];

export default function Footer() {
  return (
    <>
      {/* Stay in the loop section — Periovive style */}
      <section className="bg-white border-t border-ink-100">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="text-4xl font-extrabold text-ink-900">
            Stay in the loop<span className="text-brand-500">.</span>
          </h2>
          <p className="mt-4 text-lg text-ink-600 max-w-xl mx-auto">
            New providers, new CE drops, new features. Once a month, nothing more.
          </p>
          <form
            className="mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
            onSubmit={(e) => e.preventDefault()}
          >
            <input
              type="email"
              placeholder="you@yourclinic.com"
              className="flex-1 rounded-pill border border-ink-200 px-6 py-3 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-8 py-3 font-semibold transition-colors"
            >
              Subscribe
            </button>
          </form>
        </div>
      </section>

      {/* Dark footer */}
      <footer className="bg-ink-900 text-ink-200">
        <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-baseline gap-1 text-white font-extrabold text-xl tracking-tight">
              <span>PerioVive CE</span>
              <span className="text-brand-400">.</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed">
              Aggregated veterinary continuing education from the providers
              you trust.
            </p>
          </div>

          {/* Link columns */}
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <h3 className="text-white font-semibold mb-4">{column.title}</h3>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-200 hover:text-white transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Copyright row */}
        <div className="border-t border-ink-600 py-6">
          <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-ink-400">
            <p>© {new Date().getFullYear()} PerioVive CE. A Periovive Analytics property.</p>
            <p>Listings aggregated from publicly available sources.</p>
          </div>
        </div>
      </footer>
    </>
  );
}
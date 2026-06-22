import Link from "next/link";

const NAV_LINKS = [
  { label: "Browse CE", href: "/listings" },
  { label: "Trainers", href: "/trainers" },
];

export default function Header() {
  return (
    <header className="border-b border-ink-100 bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-baseline gap-1 text-ink-900 font-extrabold text-xl tracking-tight"
        >
          <span>PerioVive CE</span>
          <span className="text-brand-500">.</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-ink-600 hover:text-ink-900 font-medium transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* CTA */}
        <Link
          href="/listings"
          className="rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-5 py-2 font-semibold text-sm transition-colors"
        >
          Browse Listings →
        </Link>
      </div>
    </header>
  );
}
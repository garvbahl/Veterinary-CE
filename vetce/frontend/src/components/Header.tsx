import Link from "next/link";

const NAV_LINKS = [
  { label: "Browse CE", href: "/listings" },
  { label: "Trainers", href: "/trainers" },
  { label: "More CE", href: "/other-providers" },
];

export default function Header() {
  return (
    <header className="border-b border-ink-100 bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/"
          className="flex flex-col leading-tight"
        >
          <span className="text-ink-900 font-extrabold text-xl tracking-tight">
            Veterinary Dental CE
            <span className="text-brand-500">.</span>
          </span>
          <span className="text-[11px] font-medium text-ink-500 tracking-tight flex items-center gap-1">
            by
            <span className="font-extrabold tracking-tight text-[13px]">
              <span className="text-ink-900">PERIO</span>
              <span className="text-[#0FB4E7]">VIVE</span>
              <span className="align-super text-[8px] text-ink-400">™</span>
            </span>
          </span>
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
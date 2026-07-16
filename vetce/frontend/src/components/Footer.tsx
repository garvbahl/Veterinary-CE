import Link from "next/link";

const FOOTER_COLUMNS = [
  {
    title: "Browse",
    links: [
      { label: "All Listings", href: "/listings" },
      { label: "Upcoming Events", href: "/listings?sort=starts_at&order=asc" },
      { label: "Trainers", href: "/trainers" },
      { label: "More Dental CE", href: "/other-providers" },
    ],
  },
  {
    title: "PerioVive",
    links: [
      { label: "Main Site", href: "https://www.periovive.com" },
      { label: "Contact", href: "mailto:info@periovive.com" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="bg-ink-900 text-ink-200">
      <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-2 md:grid-cols-3 gap-8">
        {/* Brand column */}
        <div className="col-span-2 md:col-span-1">
          <div className="flex flex-col leading-tight text-white font-extrabold text-xl tracking-tight">
            <span>
              Veterinary Dentistry CE
              <span className="text-brand-400">.</span>
            </span>
            <span className="text-xs font-medium text-ink-400 mt-1">
              aggregated by PerioVive
            </span>
          </div>
          <p className="mt-4 text-sm leading-relaxed">
            A directory of veterinary dentistry continuing education, gathered
            from providers across the profession.
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
          <p>© {new Date().getFullYear()} PerioVive Analytics. All rights reserved.</p>
          <p className="max-w-md sm:text-right">
            Listings are aggregated from publicly available sources. Inclusion
            does not imply affiliation with or endorsement by PerioVive.
          </p>
        </div>
      </div>
    </footer>
  );
}
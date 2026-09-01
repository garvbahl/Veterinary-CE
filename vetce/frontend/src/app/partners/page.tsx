import Link from "next/link";

export const metadata = {
  title: "Our Partners — Veterinary Dental CE",
  description:
    "Organizations that partner with Veterinary Dental CE to support veterinary dental education.",
};

type Partner = {
  name: string;
  logo: string; // path under /public
  website: string;
  blurb?: string;
};

// Add new partners here. Each renders as a clickable logo card.
const PARTNERS: Partner[] = [
  {
    name: "Shipp's Dental",
    logo: "/partners/shipps-dental.jpg",
    website: "https://shippsdental.com/",
    blurb:
      "A provider of veterinary dental instruments, equipment, and education.",
  },
];

export default function PartnersPage() {
  return (
    <main>
      {/* ===== Header ===== */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">
          Our Partners
        </p>
        <h1 className="mt-2 text-3xl md:text-4xl font-extrabold text-ink-900">
          Partners in veterinary dental education
          <span className="text-brand-500">.</span>
        </h1>
        <p className="mt-3 text-ink-600 max-w-2xl">
          We&apos;re proud to work alongside these organizations who share our
          commitment to advancing veterinary dental care.
        </p>
      </section>

      {/* ===== Partner cards ===== */}
      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PARTNERS.map((p) => (
            <a
              key={p.name}
              href={p.website}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex flex-col rounded-2xl border border-ink-100 bg-white p-6 shadow-card transition-shadow hover:shadow-lg"
            >
              <div className="flex h-32 items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={p.logo}
                  alt={`${p.name} logo`}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
              <div className="mt-4">
                <h2 className="text-lg font-bold text-ink-900">{p.name}</h2>
                {p.blurb && (
                  <p className="mt-1 text-sm text-ink-600">{p.blurb}</p>
                )}
                <span className="mt-3 inline-block text-sm font-semibold text-brand-600 group-hover:text-brand-700">
                  Visit {p.name} →
                </span>
              </div>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}